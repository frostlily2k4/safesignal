from modules.privacy import pseudonym_map, redact, replace_names, sha256_bytes


def test_redacts_identifiers():
    text = "Call 9876543210 or +91 98765 43210, mail a.b@gmail.com, pay ravi@okaxis, aadhaar 1234 5678 9012, OTP is 482913"
    out = redact(text)
    for secret in ["9876543210", "98765 43210", "a.b@gmail.com", "ravi@okaxis", "1234 5678 9012", "482913"]:
        assert secret not in out
    assert "[PHONE]" in out and "[EMAIL]" in out and "[UPI_ID]" in out


def test_pseudonyms():
    mapping = pseudonym_map(["Arun", "Meena"], me="Meena")
    assert mapping == {"Arun": "Person A", "Meena": "You"}
    assert replace_names("Arun told Meena", mapping) == "Person A told You"


def test_hash_is_stable():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert len(sha256_bytes(b"abc")) == 64
