from datetime import datetime

import pytest

from modules.llm import LLMError, explain, parse_llm_json, rule_based_explanation
from modules.patterns import detect
from modules.report import analyses_to_csv, build_report_markdown
from modules.resources import steps_for
from modules.risk_timeline import MessageAnalysis, summarise


def _summary():
    seq = [MessageAnalysis(index=i, sender="A", text=t, hits=detect(t), risk=r, smoothed=r)
           for i, (t, r) in enumerate([("send me your live location", 0.5), ("I will kill you", 0.95)])]
    return seq, summarise(seq)


def test_parse_llm_json_handles_fences():
    raw = '```json\n{"summary":"s","why_flagged":"one","pattern_explanation":"p","caution":"c"}\n```'
    out = parse_llm_json(raw)
    assert out["why_flagged"] == ["one"]


def test_parse_llm_json_errors():
    with pytest.raises(LLMError):
        parse_llm_json("not json")
    with pytest.raises(LLMError):
        parse_llm_json('{"summary": "only"}')


def test_explain_without_key_uses_rules():
    _, s = _summary()
    exp, source, err = explain(s, ["x"], api_key="", model="m")
    assert source == "rules" and err is None
    assert exp == rule_based_explanation(s)


def test_explain_with_bad_key_falls_back(monkeypatch):
    import modules.llm as llm

    def boom(*a, **k):
        raise LLMError("network down")

    monkeypatch.setattr(llm, "explain_with_gemini", boom)
    _, s = _summary()
    exp, source, err = llm.explain(s, ["x"], api_key="fake", model="m")
    assert source == "rules" and "network down" in err


def test_report_and_csv():
    seq, s = _summary()
    md = build_report_markdown("abc123", s, seq, rule_based_explanation(s), steps_for(list(s.category_counts)), datetime(2026, 10, 10))
    assert "abc123" in md and "I will kill you" in md and "112" in md
    csv_bytes = analyses_to_csv(seq)
    assert csv_bytes.decode("utf-8-sig").count("\n") == 3


def test_steps_always_include_evidence_advice():
    steps = steps_for(["Threat of violence or harm"])
    assert any("112" in s for s in steps)
    assert any("Do not delete" in s for s in steps)
