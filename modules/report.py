"""Downloadable evidence summary (Markdown) and per-message analysis (CSV)."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from modules.resources import HELPLINES
from modules.risk_timeline import STAGE_NAMES, ConversationSummary, MessageAnalysis

LEVEL_TEXT = {"SAFE": "Safe", "POSSIBLE_THREAT": "Possible threat", "THREAT": "Threat"}


def _ts(a: MessageAnalysis) -> str:
    return a.timestamp.strftime("%d-%m-%Y %H:%M") if a.timestamp else "time not available"


def build_report_markdown(file_hash: str, summary: ConversationSummary, analyses: list[MessageAnalysis],
                          explanation: dict, steps: list[str], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now()
    flagged = [a for a in analyses if a.index in set(summary.flagged_indices)]
    lines = [
        "# SafeSignal evidence summary",
        "",
        f"Generated: {generated_at.strftime('%d-%m-%Y %H:%M')}",
        f"Source file SHA-256: `{file_hash or 'pasted text'}`",
        "",
        "The SHA-256 fingerprint lets you show later that the chat file was not changed after this summary was made.",
        "",
        "## Result",
        f"- Overall level: **{LEVEL_TEXT[summary.level]}**",
        f"- Messages analysed: {summary.n_analysed}; flagged: {len(flagged)}",
        f"- Escalation detected: {'Yes' if summary.escalation_detected else 'No'}",
    ]
    if summary.stages_in_order:
        lines.append("- Stages seen, in order: " + "; ".join(STAGE_NAMES[s] for s in summary.stages_in_order))
    lines += ["", "## Explanation", explanation.get("summary", ""), ""]
    lines += [f"- {w}" for w in explanation.get("why_flagged", [])]
    lines += ["", explanation.get("pattern_explanation", ""), "", f"_{explanation.get('caution', '')}_", ""]
    lines += ["## Flagged messages", "", "| # | Time | Sender | Message | Risk | Tactics |", "|---|---|---|---|---|---|"]
    for a in flagged:
        msg = a.text.replace("|", "/").replace("\n", " ")
        tactics = ", ".join(h.label for h in a.hits) or "classifier"
        lines.append(f"| {a.index + 1} | {_ts(a)} | {a.sender} | {msg} | {a.risk:.2f} | {tactics} |")
    lines += ["", "## Suggested next steps", ""] + [f"- {s}" for s in steps]
    lines += ["", "## Where to get help (India)", ""] + [f"- {h['name']}: {h['contact']} ({h['when']})" for h in HELPLINES]
    lines += ["", "Please confirm helpline details on official websites."]
    return "\n".join(lines)


def analyses_to_csv(analyses: list[MessageAnalysis]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["message_no", "timestamp", "sender", "text", "classifier_label", "classifier_risk",
                "pattern_score", "combined_risk", "level", "tactics"])
    for a in analyses:
        w.writerow([a.index + 1, _ts(a), a.sender, a.text, a.clf_label, a.clf_risk, a.pattern_score,
                    a.risk, a.level, "; ".join(h.label for h in a.hits)])
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel opens Tamil/₹ correctly
