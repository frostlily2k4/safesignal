"""Explainable risk-pattern detection (English + Tamil/English code-mixed).

Each category is a recognised tactic from online harassment, grooming,
sextortion and scam playbooks. Matches are shown to the user verbatim so
every flag can be traced to the words that triggered it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# stage: rough position on an escalation ladder (1 = early pressure, 4 = explicit harm)
CATEGORIES: dict[str, dict] = {
    "location_tracking": {
        "label": "Asking for or tracking location",
        "weight": 0.30,
        "stage": 1,
        "patterns": [
            r"\b(send|share)\s+(me\s+)?(your\s+)?(live\s+)?location\b",
            r"\bwhere\s+(are|r)\s+(you|u)\s+(now|right now|exactly)\b",
            r"\benga\s+(iruka|irukka|irukeenga|irukinga)\b",
            r"\blocation\s+(anuppu|anupu|podu|share\s+pannu)\b",
        ],
    },
    "isolation_secrecy": {
        "label": "Pushing secrecy or isolation",
        "weight": 0.35,
        "stage": 2,
        "patterns": [
            r"\bdon'?t\s+tell\s+(anyone|anybody|your\s+(parents|family|friends|mom|dad|amma|appa))\b",
            r"\b(delete|clear)\s+(this|the|our)\s+(chat|messages?|conversation)\b",
            r"\b(our|this\s+is\s+our)\s+(little\s+)?secret\b",
            r"\b(yaar\s*kitta(yum)?|yarukkum)\s+(solla\s*(kudathu|kudadhu|thaa?dha)|sollatha|sollaadha)\b",
            r"\bsecret\s*(ah|aa)\s+(vechuko|vachuko|irukkattum)\b",
        ],
    },
    "meeting_pressure": {
        "label": "Pressure to meet alone",
        "weight": 0.35,
        "stage": 2,
        "patterns": [
            r"\b(come|meet\s+me)\s+alone\b",
            r"\bdon'?t\s+bring\s+(anyone|your\s+friends?)\b",
            r"\bthani(ya|yaa|aa)\s+(vaa|va|vanga)\b",
        ],
    },
    "image_request": {
        "label": "Requesting private photos",
        "weight": 0.45,
        "stage": 3,
        "patterns": [
            r"\bsend\s+(me\s+)?(a\s+|some\s+|your\s+)?(private\s+|hot\s+|nude\s+)?(pic|pics|photo|photos|picture|pictures|selfie)\b",
            r"\b(photo|pic|selfie)\s+(anuppu|anupu|anuppunga|podu)\b",
            r"\bvideo\s+call\s+(now|alone|pannu)\b",
        ],
    },
    "coercion_blackmail": {
        "label": "Coercion or blackmail",
        "weight": 0.60,
        "stage": 4,
        "patterns": [
            r"\b(leak|post|share|upload|send)\s+(your\s+|these\s+|the\s+)?(pics|photos|pictures|videos?|chats?)\b.*\b(if|unless|or\s+else)\b",
            r"\b(if|unless)\s+you\s+(don'?t|do\s+not)\b.*\b(leak|post|share|everyone|parents|viral)\b",
            r"\bgo\s+viral\b",
            r"\b(viral\s+aa?kiduven|viral\s+pannuven|leak\s+pannuven)\b",
            r"\byou\s+owe\s+me\b",
            r"\blast\s+(chance|warning)\b",
        ],
    },
    "violent_threat": {
        "label": "Threat of violence or harm",
        "weight": 0.85,
        "stage": 4,
        "patterns": [
            r"\b(i('ll| will)|gonna|going\s+to)\s+(kill|hurt|beat|finish|destroy)\s+(you|u|her|your)\b",
            r"\bkill\s+(you|u)\b",
            r"\byou('ll| will)\s+regret\b",
            r"\bacid\b",
            r"\b(kolluven|kollidu?ven|adippen|adichiduven|vida\s+maaten|vida\s+maatten)\b",
        ],
    },
    "stalking_monitoring": {
        "label": "Watching or following",
        "weight": 0.50,
        "stage": 3,
        "patterns": [
            r"\bi\s+(saw|watched|followed)\s+you\b",
            r"\bi\s+know\s+where\s+you\s+(live|stay|study|work)\b",
            r"\b(outside|near|in\s+front\s+of)\s+your\s+(house|home|hostel|college|office|room|pg)\b",
            r"\b(following|watching)\s+you\b",
            r"\b(un|unga|unnoda)\s+(veedu|veetu|hostel|college)\s+(kitta|pakkathula|munnadi)\b",
        ],
    },
    "distress": {
        "label": "Call for help or immediate danger",
        "weight": 0.75,
        "stage": 4,
        "patterns": [
            r"^\s*(help|help me|please help|save me)\b",
            r"\b(help me|save me)\b.*\b(please|now|fast|scared)\b",
            r"\bsome(one|body)\s+is\s+(following|chasing|touching)\s+me\b",
            r"\b(call|get)\s+(the\s+)?(police|112|100)\b",
            r"\b(kaapathunga|kaappathunga|bayama\s+irukku)\b",
        ],
    },
    "financial_scam": {
        "label": "Money or OTP pressure (possible scam)",
        "weight": 0.45,
        "stage": 3,
        "patterns": [
            r"\b(share|send|tell)\s+(me\s+)?(the\s+|your\s+)?otp\b",
            r"\b(send|transfer|pay)\s+(me\s+)?(rs\.?|₹|inr)?\s?\d{2,}\b",
            r"\b(kyc|account)\s+(will\s+be\s+)?(blocked|suspended|expired)\b",
            r"\b(panam|panam\s+anuppu|gpay\s+pannu|money\s+anuppu)\b",
            r"\bpay\s+(the\s+)?(fine|fee|penalty|charges)\b",
        ],
    },
}

_COMPILED = {
    key: [re.compile(p, re.IGNORECASE) for p in spec["patterns"]] for key, spec in CATEGORIES.items()
}


@dataclass
class PatternHit:
    category: str
    label: str
    matched: str
    stage: int
    weight: float


def detect(text: str) -> list[PatternHit]:
    hits: list[PatternHit] = []
    if not text:
        return hits
    for key, regexes in _COMPILED.items():
        for rx in regexes:
            m = rx.search(text)
            if m:
                spec = CATEGORIES[key]
                hits.append(PatternHit(key, spec["label"], m.group(0), spec["stage"], spec["weight"]))
                break  # one hit per category per message is enough
    return hits


def pattern_score(hits: list[PatternHit]) -> float:
    """Noisy-OR over distinct categories, so several weak signals add up
    but the score never exceeds 1."""
    remaining = 1.0
    for w in {h.category: h.weight for h in hits}.values():
        remaining *= 1.0 - w
    return round(1.0 - remaining, 4)
