from modules.chat_parser import detect_format, parse_chat, senders

ANDROID = """02/10/26, 7:02 pm - Messages and calls are end-to-end encrypted.
02/10/26, 7:02 pm - Arun: Hi there
02/10/26, 7:04 pm - Meena: Who is this?
second line of Meena's message
02/10/26, 7:05 pm - Arun: <Media omitted>
02/10/26, 21:15 - Arun: 24 hour time works too"""

IOS = """[06/10/26, 8:10:12 PM] Karthik: Hi Divya
[06/10/26, 8:12:40\u202fPM] Divya: Nalla irukken"""


def test_android_format():
    msgs = parse_chat(ANDROID)
    assert detect_format(ANDROID) == "whatsapp"
    assert [m.sender for m in msgs] == ["Arun", "Meena", "Arun"]
    assert msgs[1].text == "Who is this?\nsecond line of Meena's message"
    assert msgs[0].timestamp.day == 2 and msgs[0].timestamp.month == 10 and msgs[0].timestamp.hour == 19
    assert msgs[2].timestamp.hour == 21


def test_ios_format_with_narrow_space():
    msgs = parse_chat(IOS)
    assert [m.sender for m in msgs] == ["Karthik", "Divya"]
    assert msgs[1].timestamp.hour == 20


def test_plain_format_and_unknown_lines():
    msgs = parse_chat("Ravi: hello\nPriya: hi\njust a line with no sender")
    assert detect_format("Ravi: hello") == "plain"
    assert [m.sender for m in msgs] == ["Ravi", "Priya"]
    assert "no sender" in msgs[1].text
    only_lines = parse_chat("first line\nsecond line")
    assert [m.sender for m in only_lines] == ["Unknown", "Unknown"]


def test_empty_and_limits():
    assert parse_chat("") == []
    many = "\n".join(f"A: message {i}" for i in range(50))
    assert len(parse_chat(many, max_messages=10)) == 10


def test_senders_sorted_by_count():
    msgs = parse_chat("A: 1\nB: 2\nA: 3")
    assert senders(msgs) == ["A", "B"]
