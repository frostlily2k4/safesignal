"""Next steps and India-specific help contacts.

Contact details were correct to the best of the author's knowledge when written;
always confirm on the official websites before relying on them.
"""
from __future__ import annotations

HELPLINES = [
    {"name": "Emergency Response (police, fire, ambulance)", "contact": "112", "when": "You feel unsafe right now"},
    {"name": "Women Helpline", "contact": "181", "when": "Harassment, threats, or you need support and referral"},
    {"name": "National Cyber Crime Helpline", "contact": "1930", "when": "Money lost or demanded online; call as early as possible"},
    {"name": "National Cyber Crime Reporting Portal", "contact": "https://cybercrime.gov.in", "when": "File a complaint about online harassment, sextortion or fraud"},
    {"name": "National Commission for Women (WhatsApp)", "contact": "7827170170", "when": "Complaints and support for women"},
    {"name": "StopNCII.org", "contact": "https://stopncii.org", "when": "Someone threatens to share your intimate images"},
    {"name": "Childline", "contact": "1098", "when": "The person being targeted is under 18"},
]

GENERAL_STEPS = [
    "Do not delete the chat. Take screenshots that show the sender's name or number, the date and the time.",
    "Export the chat (WhatsApp: open chat, More, Export chat) and keep a copy somewhere only you can access.",
    "Tell one person you trust what is happening.",
]

CATEGORY_STEPS = {
    "Asking for or tracking location": [
        "Turn off live location sharing for this person and check which apps can see your location.",
    ],
    "Pushing secrecy or isolation": [
        "Requests to keep things secret are a warning sign. Share the conversation with someone you trust.",
    ],
    "Pressure to meet alone": [
        "Do not meet alone. If you choose to meet, pick a busy public place and tell someone where you will be.",
    ],
    "Requesting private photos": [
        "You do not have to send any photo. Saying no and blocking is a complete answer.",
    ],
    "Coercion or blackmail": [
        "Do not pay or send anything more; demands usually increase after the first payment.",
        "Report on cybercrime.gov.in and, for image threats, create a case on StopNCII.org.",
    ],
    "Threat of violence or harm": [
        "If you are in danger now, call 112.",
        "Keep the threatening messages as evidence and report them to the police or on cybercrime.gov.in.",
    ],
    "Watching or following": [
        "Vary your routine for a while and let family, hostel staff or security know.",
    ],
    "Call for help or immediate danger": [
        "If you or someone else is in danger now, call 112 and move to a crowded, well-lit place.",
    ],
    "Money or OTP pressure (possible scam)": [
        "Never share an OTP. Banks and government offices do not ask for it on chat.",
        "If money has already gone, call 1930 immediately; reporting early improves the chance of freezing it.",
    ],
}


def steps_for(category_labels) -> list[str]:
    steps: list[str] = []
    for label in category_labels:
        for s in CATEGORY_STEPS.get(label, []):
            if s not in steps:
                steps.append(s)
    return steps + [s for s in GENERAL_STEPS if s not in steps]
