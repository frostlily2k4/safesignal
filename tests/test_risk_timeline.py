from config import POSSIBLE_THRESHOLD, THREAT_THRESHOLD, SAMPLE_CHATS_DIR
from modules.chat_parser import parse_chat
from modules.risk_timeline import MessageAnalysis, analyse_messages, analyse_text, combine, level_for, summarise
from modules.patterns import detect


def test_combine_bounds_and_floor():
    assert combine(0.0, 0.0) == 0.0
    assert combine(0.15, 0.0) == 0.0  # below classifier floor
    assert combine(1.0, 0.0) <= 0.9
    assert 0.9 < combine(1.0, 0.8) <= 1.0


def test_levels():
    assert level_for(POSSIBLE_THRESHOLD - 0.01) == "SAFE"
    assert level_for(POSSIBLE_THRESHOLD) == "POSSIBLE_THREAT"
    assert level_for(THREAT_THRESHOLD) == "THREAT"


def _a(i, text, risk):
    return MessageAnalysis(index=i, sender="X", text=text, hits=detect(text), risk=risk, smoothed=risk)


def test_ladder_escalation():
    seq = [
        _a(0, "hi", 0.0),
        _a(1, "send me your live location", 0.4),
        _a(2, "don't tell anyone", 0.45),
        _a(3, "send me a pic", 0.6),
        _a(4, "I will kill you", 0.95),
    ]
    s = summarise(seq)
    assert s.escalation_detected
    assert s.stages_in_order == [1, 2, 3, 4]
    assert s.level == "THREAT"
    assert s.flagged_indices == [1, 2, 3, 4]


def test_no_escalation_for_flat_safe_chat():
    s = summarise([_a(i, "see you at college", 0.05) for i in range(6)])
    assert not s.escalation_detected and s.level == "SAFE" and s.flagged_indices == []


def test_empty_summary():
    assert summarise([]).n_analysed == 0


def test_end_to_end_samples(model):
    esc = parse_chat((SAMPLE_CHATS_DIR / "escalating_chat_android.txt").read_text(encoding="utf-8"))
    s = summarise(analyse_messages(model, esc, me="Meena"))
    assert s.level == "THREAT" and s.escalation_detected
    safe = parse_chat((SAMPLE_CHATS_DIR / "safe_chat_android.txt").read_text(encoding="utf-8"))
    s2 = summarise(analyse_messages(model, safe))
    assert s2.level == "SAFE"


def test_me_messages_skipped(model):
    msgs = parse_chat("A: hi\nB: I will kill you\nA: ok")
    out = analyse_messages(model, msgs, me="B")
    assert all(a.sender == "A" for a in out)


def test_single_message(model):
    assert analyse_text(model, "I will kill you").level == "THREAT"
    assert analyse_text(model, "hi").level == "SAFE"
