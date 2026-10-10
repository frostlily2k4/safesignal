"""Combine classifier + pattern signals per message, then look at the whole
conversation: smoothed risk over time, escalation, and which tactic stages
appeared in what order."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from config import ESCALATION_DELTA, POSSIBLE_THRESHOLD, THREAT_THRESHOLD
from modules.chat_parser import ChatMessage
from modules.classifier import Prediction, predict
from modules.patterns import PatternHit, detect, pattern_score

STAGE_NAMES = {
    1: "Probing (location, availability)",
    2: "Isolating (secrecy, meet alone)",
    3: "Exploiting (photos, money, following)",
    4: "Threatening (blackmail, violence)",
}


@dataclass
class MessageAnalysis:
    index: int
    sender: str
    text: str
    timestamp: object = None
    clf_label: str = "SAFE"
    clf_probs: dict = field(default_factory=dict)
    clf_risk: float = 0.0
    hits: list[PatternHit] = field(default_factory=list)
    pattern_score: float = 0.0
    risk: float = 0.0
    smoothed: float = 0.0
    level: str = "SAFE"


@dataclass
class ConversationSummary:
    level: str
    peak_risk: float
    peak_smoothed: float
    escalation_detected: bool
    escalation_delta: float
    stages_in_order: list[int]
    category_counts: dict
    flagged_indices: list[int]
    n_analysed: int


CLF_FLOOR = 0.2  # classifier risk below this is treated as background noise


def combine(clf_risk: float, p_score: float) -> float:
    """Noisy-OR of the two signals. Classifier risk under CLF_FLOOR is ignored
    (a small, templated training set gives everyday text some residual risk),
    and the classifier is capped at 0.9 so it can't reach certainty alone."""
    clf = max(0.0, (clf_risk - CLF_FLOOR) / (1.0 - CLF_FLOOR))
    return round(1.0 - (1.0 - 0.9 * clf) * (1.0 - p_score), 4)


def level_for(score: float) -> str:
    if score >= THREAT_THRESHOLD:
        return "THREAT"
    if score >= POSSIBLE_THRESHOLD:
        return "POSSIBLE_THREAT"
    return "SAFE"


def _message_risk(text: str, clf_risk: float, hits) -> float:
    """Very short messages carry little evidence, so without a matched tactic
    the classifier's say is halved for messages of two words or fewer."""
    if not hits and len(text.split()) <= 2:
        clf_risk *= 0.5
    return combine(clf_risk, pattern_score(hits))


def analyse_text(pipe, text: str) -> MessageAnalysis:
    pred: Prediction = predict(pipe, [text])[0]
    hits = detect(text)
    ps = pattern_score(hits)
    risk = _message_risk(text, pred.risk, hits)
    return MessageAnalysis(0, "", text, None, pred.label, pred.probs, pred.risk, hits, ps, risk, risk, level_for(risk))


def analyse_messages(pipe, messages: list[ChatMessage], me: str | None = None, alpha: float = 0.5) -> list[MessageAnalysis]:
    """Score messages sent by people other than `me` (all messages if me is None)."""
    targets = [(i, m) for i, m in enumerate(messages) if me is None or m.sender != me]
    preds = predict(pipe, [m.text for _, m in targets])
    out: list[MessageAnalysis] = []
    smoothed = 0.0
    for (i, m), pred in zip(targets, preds):
        hits = detect(m.text)
        ps = pattern_score(hits)
        risk = _message_risk(m.text, pred.risk, hits)
        smoothed = risk if not out else alpha * risk + (1 - alpha) * smoothed
        out.append(
            MessageAnalysis(
                index=i,
                sender=m.sender,
                text=m.text,
                timestamp=m.timestamp,
                clf_label=pred.label,
                clf_probs=pred.probs,
                clf_risk=round(pred.risk, 4),
                hits=hits,
                pattern_score=ps,
                risk=risk,
                smoothed=round(smoothed, 4),
                level=level_for(risk),
            )
        )
    return out


def summarise(analyses: list[MessageAnalysis]) -> ConversationSummary:
    if not analyses:
        return ConversationSummary("SAFE", 0.0, 0.0, False, 0.0, [], {}, [], 0)
    risks = [a.risk for a in analyses]
    n = len(risks)
    if n >= 3:
        k = max(1, n // 3)
        late_mean = sum(risks[-k:]) / k
        delta = late_mean - sum(risks[:k]) / k
    else:
        late_mean, delta = 0.0, 0.0

    first_seen: dict[int, int] = {}
    counts: Counter = Counter()
    for pos, a in enumerate(analyses):
        for h in a.hits:
            counts[h.label] += 1
            first_seen.setdefault(h.stage, pos)
    stages_in_order = sorted(first_seen, key=lambda s: first_seen[s])
    # "ladder climb": two or more stages, appearing in increasing order
    ladder = len(stages_in_order) >= 2 and stages_in_order == sorted(stages_in_order)

    peak = max(risks)
    return ConversationSummary(
        level=level_for(peak),
        peak_risk=round(peak, 4),
        peak_smoothed=round(max(a.smoothed for a in analyses), 4),
        # a rise only counts if the end of the chat is itself concerning
        escalation_detected=bool((delta >= ESCALATION_DELTA and late_mean >= POSSIBLE_THRESHOLD) or ladder),
        escalation_delta=round(delta, 4),
        stages_in_order=stages_in_order,
        category_counts=dict(counts),
        flagged_indices=[a.index for a in analyses if a.risk >= POSSIBLE_THRESHOLD],
        n_analysed=n,
    )
