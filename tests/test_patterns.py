from modules.patterns import detect, pattern_score


def cats(text):
    return {h.category for h in detect(text)}


def test_english_tactics():
    assert "location_tracking" in cats("Send me your live location now")
    assert "isolation_secrecy" in cats("Don't tell your parents about us")
    assert "image_request" in cats("send me a pic")
    assert "coercion_blackmail" in cats("If you don't reply I will leak your photos to everyone")
    assert "violent_threat" in cats("I will kill you")
    assert "financial_scam" in cats("Share the OTP you just got")
    assert "distress" in cats("help me please, someone is following me")


def test_tanglish_tactics():
    assert "location_tracking" in cats("Enga iruka ippo? Location anuppu")
    assert "isolation_secrecy" in cats("Yaarkittayum sollatha")
    assert "image_request" in cats("Photo anuppu")
    assert "violent_threat" in cats("Vida maaten unna")


def test_harmless_phrases_not_flagged():
    for text in ["This traffic is killing me", "I'll kill this exam", "Happy birthday!", "See you at the library"]:
        assert cats(text) == set(), text


def test_pattern_score_noisy_or():
    assert pattern_score([]) == 0.0
    one = pattern_score(detect("send me a pic"))
    two = pattern_score(detect("send me a pic and don't tell anyone"))
    assert 0 < one < two < 1
