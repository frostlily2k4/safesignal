"""SafeSignal: spot warning signs in chats, see how they escalate, and know what to do next.

Run:  streamlit run app.py
"""
from __future__ import annotations

import json
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import config
from modules.chat_parser import parse_chat, senders
from modules.classifier import load_model, save_model, train_and_evaluate
from modules.llm import explain
from modules.privacy import pseudonym_map, redact, replace_names, sha256_bytes
from modules.report import analyses_to_csv, build_report_markdown
from modules.resources import HELPLINES, steps_for
from modules.risk_timeline import STAGE_NAMES, analyse_messages, analyse_text, summarise

st.set_page_config(page_title="SafeSignal", page_icon="🛡️", layout="wide")

LEVEL_STYLE = {
    "SAFE": ("#1B7F6B", "No clear warning signs", "Nothing here matches known harassment or scam tactics."),
    "POSSIBLE_THREAT": ("#A86A00", "Some warning signs", "Some messages match tactics often used to pressure or control someone."),
    "THREAT": ("#B3261E", "Serious warning signs", "This contains threats, blackmail or a request for help. Please read the steps below."),
}

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stTextArea textarea, button, input { font-family: 'Atkinson Hyperlegible', system-ui, sans-serif; }
.block-container { max-width: 1100px; padding-top: 2rem; }
.verdict { border-left: 10px solid var(--c); background: color-mix(in srgb, var(--c) 9%, white);
           padding: 1.1rem 1.4rem; border-radius: 4px; margin: 0.5rem 0 1.2rem 0; }
.verdict h2 { color: var(--c); margin: 0 0 .25rem 0; font-size: 1.6rem; }
.verdict p { margin: 0; color: #1C2230; }
.tactic { display:inline-block; border:1px solid #C9CEDA; border-radius: 999px; padding: 2px 10px;
          margin: 2px 4px 2px 0; font-size: .85rem; background: #fff; }
.small-note { color:#5A6273; font-size:.85rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------- model loading ----------
@st.cache_resource(show_spinner="Preparing the classifier…")
def get_model():
    if config.MODEL_PATH.exists():
        return load_model(config.MODEL_PATH)
    pipe, metrics = train_and_evaluate(config.training_files(), config.PROBE_PATH)
    save_model(pipe, metrics, config.MODEL_PATH, config.METRICS_PATH)
    return pipe


def get_metrics() -> dict:
    try:
        return json.loads(config.METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


try:
    MODEL = get_model()
except (FileNotFoundError, ValueError) as exc:
    st.error(f"The classifier could not be loaded or trained: {exc}")
    st.stop()


# ---------- helpers ----------
def verdict_block(level: str, extra: str = "") -> None:
    colour, title, text = LEVEL_STYLE[level]
    st.markdown(
        f'<div class="verdict" style="--c:{colour}"><h2>{title}</h2><p>{text}{(" " + extra) if extra else ""}</p></div>',
        unsafe_allow_html=True,
    )


def tactic_chips(hits) -> str:
    return "".join(f'<span class="tactic">{h.label}: “{h.matched}”</span>' for h in hits)


def show_help(category_labels) -> None:
    st.subheader("What you can do")
    for s in steps_for(category_labels):
        st.markdown(f"- {s}")
    with st.expander("Where to get help in India"):
        for h in HELPLINES:
            st.markdown(f"**{h['name']}**: {h['contact']}  \n{h['when']}")
        st.caption("Please confirm these numbers on official websites.")


# ---------- sidebar ----------
api_key = config.gemini_api_key()
with st.sidebar:
    st.header("🛡️ SafeSignal")
    st.write("Checks chats for harassment, grooming, sextortion and scam tactics, in English and Tanglish.")
    use_llm = st.toggle(
        "Plain-language explanations with Gemini",
        value=bool(api_key),
        disabled=not api_key,
        help="Only redacted excerpts are sent: names become Person A/B, numbers and IDs are removed.",
    )
    if api_key:
        st.caption(f"Gemini connected ({config.gemini_model()}).")
    else:
        st.caption("No Gemini key set. Explanations use the built-in rules, which work offline.")
    st.divider()
    st.caption("Your chat is analysed in memory and never saved by the app.")

st.title("SafeSignal")
st.write("See the warning signs in a chat, how they build up over time, and what to do next.")

tab_msg, tab_chat, tab_how = st.tabs(["Check a message", "Analyse a chat", "How it works"])

# ---------- tab 1: single message ----------
with tab_msg:
    text = st.text_area(
        "Paste one message",
        height=110,
        max_chars=config.MAX_SINGLE_MESSAGE_CHARS,
        placeholder="e.g. Enga iruka ippo? Location anuppu",
    )
    if st.button("Check message", type="primary"):
        if not text.strip():
            st.warning("Paste a message first.")
        else:
            a = analyse_text(MODEL, text.strip())
            verdict_block(a.level)
            c1, c2, c3 = st.columns(3)
            c1.metric("Combined risk", f"{a.risk:.2f}")
            c2.metric("Classifier says", a.clf_label.replace("_", " ").title())
            c3.metric("Tactics matched", len(a.hits))
            if a.hits:
                st.markdown(tactic_chips(a.hits), unsafe_allow_html=True)
            probs = pd.DataFrame({"Label": list(a.clf_probs), "Probability": list(a.clf_probs.values())})
            st.altair_chart(
                alt.Chart(probs).mark_bar().encode(
                    x=alt.X("Probability:Q", scale=alt.Scale(domain=[0, 1])),
                    y=alt.Y("Label:N", sort=config.LABELS, title=None),
                    color=alt.Color("Label:N", scale=alt.Scale(domain=config.LABELS, range=["#1B7F6B", "#A86A00", "#B3261E"]), legend=None),
                ).properties(height=120),
                width="stretch",
            )
            if a.level != "SAFE":
                show_help([h.label for h in a.hits])

# ---------- tab 2: whole chat ----------
with tab_chat:
    source = st.radio("Chat source", ["Try a sample chat", "Upload WhatsApp export (.txt)", "Paste chat text"], horizontal=True)
    raw_text, raw_bytes = "", b""
    if source == "Upload WhatsApp export (.txt)":
        st.caption("WhatsApp: open the chat, tap ⋮ or the name, choose Export chat, then Without media.")
        up = st.file_uploader("Chat file", type=["txt"])
        if up is not None:
            raw_bytes = up.getvalue()
            if len(raw_bytes) > config.MAX_UPLOAD_BYTES:
                st.error("This file is larger than 2 MB. Export a shorter chat or remove older messages.")
                raw_bytes = b""
            else:
                raw_text = raw_bytes.decode("utf-8", errors="replace")
    elif source == "Paste chat text":
        raw_text = st.text_area("Paste the chat", height=200, placeholder="Name: message\nName: message")
        raw_bytes = raw_text.encode("utf-8")
    else:
        samples = sorted(config.SAMPLE_CHATS_DIR.glob("*.txt"))
        if not samples:
            st.info("No sample chats found in assets/sample_chats.")
        else:
            choice = st.selectbox("Sample", samples, format_func=lambda p: p.stem.replace("_", " ").capitalize())
            raw_bytes = choice.read_bytes()
            raw_text = raw_bytes.decode("utf-8")
            with st.expander("Preview sample"):
                st.text(raw_text)

    messages = parse_chat(raw_text) if raw_text.strip() else []
    if raw_text.strip() and not messages:
        st.warning("No messages could be read. Check the file is a WhatsApp .txt export or lines like 'Name: message'.")

    if messages:
        people = senders(messages)
        me_choice = st.selectbox(
            "Which participant are you? Their messages are skipped so only the other side is checked.",
            ["Check everyone"] + people,
        )
        me = None if me_choice == "Check everyone" else me_choice
        st.caption(f"{len(messages)} messages read from {len(people)} participant(s).")

        if st.button("Analyse chat", type="primary"):
            analyses = analyse_messages(MODEL, messages, me)
            if not analyses:
                st.warning("There are no messages from other participants to check.")
            else:
                summary = summarise(analyses)
                names = pseudonym_map(people, me)
                flagged = [a for a in analyses if a.index in set(summary.flagged_indices)]
                excerpts = [
                    f"[msg {a.index + 1}] {names.get(a.sender, 'Person')}: {replace_names(redact(a.text), names)}"
                    for a in flagged[: config.MAX_LLM_EXCERPTS]
                ]
                with st.spinner("Writing the explanation…"):
                    explanation, exp_source, exp_error = explain(
                        summary, excerpts, api_key, config.gemini_model(), use_llm=use_llm
                    )
                st.session_state["chat_result"] = {
                    "analyses": analyses,
                    "summary": summary,
                    "explanation": explanation,
                    "source": exp_source,
                    "error": exp_error,
                    "hash": sha256_bytes(raw_bytes) if raw_bytes else "",
                    "excerpts": excerpts,
                    "key": (sha256_bytes(raw_text.encode("utf-8")), me),
                }

    result = st.session_state.get("chat_result")
    current_key = (sha256_bytes(raw_text.encode("utf-8")), me) if messages else None
    if result and messages and result.get("key") == current_key:
        analyses, summary, explanation = result["analyses"], result["summary"], result["explanation"]
        extra = "The risk builds up over the conversation." if summary.escalation_detected else ""
        verdict_block(summary.level, extra)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Messages checked", summary.n_analysed)
        c2.metric("Flagged", len(summary.flagged_indices))
        c3.metric("Highest risk", f"{summary.peak_risk:.2f}")
        c4.metric("Escalation", "Yes" if summary.escalation_detected else "No")

        st.subheader("Risk across the conversation")
        df = pd.DataFrame(
            {
                "Message": [a.index + 1 for a in analyses],
                "Risk": [a.risk for a in analyses],
                "Trend": [a.smoothed for a in analyses],
                "Level": [a.level for a in analyses],
                "Text": [a.text[:90] for a in analyses],
                "Tactics": [", ".join(h.label for h in a.hits) or "none" for a in analyses],
            }
        )
        base = alt.Chart(df).encode(x=alt.X("Message:Q", title="Message number", axis=alt.Axis(tickMinStep=1)))
        bands = alt.Chart(
            pd.DataFrame({"y": [0, config.POSSIBLE_THRESHOLD, config.THREAT_THRESHOLD],
                          "y2": [config.POSSIBLE_THRESHOLD, config.THREAT_THRESHOLD, 1.0],
                          "Level": config.LABELS})
        ).mark_rect(opacity=0.08).encode(
            y="y:Q", y2="y2:Q",
            color=alt.Color("Level:N", scale=alt.Scale(domain=config.LABELS, range=["#1B7F6B", "#A86A00", "#B3261E"]), legend=None),
        )
        trend = base.mark_line(color="#3E4C9A", strokeWidth=3).encode(y=alt.Y("Trend:Q", scale=alt.Scale(domain=[0, 1]), title="Risk"))
        points = base.mark_circle(size=110).encode(
            y="Risk:Q",
            color=alt.Color("Level:N", scale=alt.Scale(domain=config.LABELS, range=["#1B7F6B", "#A86A00", "#B3261E"]), title="Message level"),
            tooltip=["Message", "Text", alt.Tooltip("Risk:Q", format=".2f"), "Tactics"],
        )
        st.altair_chart((bands + trend + points).properties(height=320), width="stretch")
        st.caption("Dots are single messages; the line is the running trend. Hover a dot to read the message.")

        if summary.stages_in_order:
            st.subheader("How the behaviour progressed")
            for n, s in enumerate(summary.stages_in_order, 1):
                st.markdown(f"{n}. {STAGE_NAMES[s]}")

        st.subheader("Why it was flagged")
        if result["source"] == "gemini":
            st.caption("Explanation written by Gemini from redacted excerpts. The risk level itself comes from SafeSignal's own model and rules.")
        else:
            st.caption("Explanation from SafeSignal's built-in rules.")
            if result["error"]:
                st.info(f"Gemini was not used: {result['error']}")
        st.write(explanation["summary"])
        for w in explanation["why_flagged"]:
            st.markdown(f"- {w}")
        st.write(explanation["pattern_explanation"])
        st.caption(explanation["caution"])

        flagged = [a for a in analyses if a.index in set(summary.flagged_indices)]
        if flagged:
            with st.expander(f"Flagged messages ({len(flagged)})", expanded=True):
                for a in flagged:
                    ts = a.timestamp.strftime("%d %b %Y, %I:%M %p") if a.timestamp else ""
                    st.markdown(f"**#{a.index + 1} · {a.sender}** <span class='small-note'>{ts} · risk {a.risk:.2f}</span>", unsafe_allow_html=True)
                    st.write(a.text)
                    if a.hits:
                        st.markdown(tactic_chips(a.hits), unsafe_allow_html=True)
        if result["excerpts"]:
            with st.expander("What was shared with the explanation model"):
                st.caption("This is exactly the redacted text the explanation step received.")
                st.code("\n".join(result["excerpts"]), language=None)

        show_help(list(summary.category_counts))

        steps = steps_for(list(summary.category_counts))
        report = build_report_markdown(result["hash"], summary, analyses, explanation, steps, datetime.now())
        d1, d2 = st.columns(2)
        d1.download_button("Download evidence summary (.md)", report, file_name="safesignal_evidence_summary.md", mime="text/markdown")
        d2.download_button("Download message analysis (.csv)", analyses_to_csv(analyses), file_name="safesignal_analysis.csv", mime="text/csv")

# ---------- tab 3: how it works ----------
with tab_how:
    st.subheader("Three layers, each with one job")
    st.markdown(
        """
1. **Message classifier** (TF-IDF word and character n-grams + logistic regression) rates each message SAFE, POSSIBLE_THREAT or THREAT. Character n-grams help with Tanglish spelling variation.
2. **Tactic detector** matches known harassment, grooming, sextortion and scam tactics in English and Tanglish, and shows the exact words that matched.
3. **Conversation analysis** combines both signals per message, tracks the running trend, and checks whether tactics appear in an escalating order (probing, isolating, exploiting, threatening).

An optional LLM (Gemini) only writes the plain-language explanation from redacted excerpts. It never sets the risk level.
"""
    )
    m = get_metrics()
    if m:
        st.subheader("Classifier evaluation")
        c1, c2, c3 = st.columns(3)
        c1.metric("Held-out accuracy", f"{m.get('test_accuracy', 0):.0%}")
        c2.metric("Held-out macro F1", f"{m.get('test_macro_f1', 0):.2f}")
        if "probe_accuracy" in m:
            c3.metric("Hand-written probe set", f"{m['probe_accuracy']:.0%}", help=f"{m.get('probe_size', 0)} realistic messages not built from training templates")
        cm = m.get("confusion_matrix")
        if cm:
            st.caption("Confusion matrix on the held-out set (rows = true label, columns = predicted)")
            st.dataframe(pd.DataFrame(cm["matrix"], index=cm["labels"], columns=cm["labels"]), width="stretch")
        st.caption(f"Trained on {m.get('n_samples', 0)} labelled messages: {m.get('label_counts', {})}")
        if m.get("probe_errors"):
            with st.expander("Where the classifier still gets it wrong"):
                st.dataframe(pd.DataFrame(m["probe_errors"]), width="stretch")
    st.subheader("Privacy")
    st.markdown(
        "- Chats are processed in memory and not stored by the app.\n"
        "- Before anything is sent to Gemini: names become *Person A / Person B*, and phone numbers, emails, UPI IDs, card and ID numbers and OTPs are removed.\n"
        "- The evidence summary includes a SHA-256 fingerprint of the original file, so you can later show it was not changed."
    )
    st.subheader("Limits")
    st.markdown(
        "- The starter dataset is small and partly synthetic, so the model can miss new phrasings or flag harmless ones.\n"
        "- It reads text only: no images, voice notes or sarcasm detection.\n"
        "- It supports decisions; it does not replace police, legal or counselling help."
    )
