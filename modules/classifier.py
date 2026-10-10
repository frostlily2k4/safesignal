"""Message-level classifier: TF-IDF (word + character n-grams) + Logistic Regression.

Character n-grams make the model more tolerant of spelling variation and
Tamil/English (Tanglish) code-mixed text, where the same word is written
many ways ("enga iruka", "enga irukka", "engeirukka").
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from config import LABELS


@dataclass
class Prediction:
    label: str
    probs: dict = field(default_factory=dict)
    risk: float = 0.0  # 0-1: P(POSSIBLE)*0.5 + P(THREAT)


def build_pipeline() -> Pipeline:
    features = FeatureUnion(
        [
            ("word", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)),
            (
                "char",
                TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True),
            ),
        ]
    )
    clf = LogisticRegression(max_iter=3000, class_weight="balanced", C=4.0)
    return Pipeline([("features", features), ("clf", clf)])


def load_dataset(paths) -> pd.DataFrame:
    """Load and merge one or more CSV files with 'text' and 'label' columns."""
    if isinstance(paths, (str, Path)):
        paths = [paths]
    frames = []
    for path in map(Path, paths):
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found at {path}. Put a CSV with 'text' and 'label' columns there.")
        part = pd.read_csv(path)
        part.columns = [c.strip().lower() for c in part.columns]
        missing = {"text", "label"} - set(part.columns)
        if missing:
            raise ValueError(f"{path.name} is missing column(s): {', '.join(sorted(missing))}")
        frames.append(part[["text", "label"]])
    if not frames:
        raise FileNotFoundError("No training CSV files found in data/.")
    df = pd.concat(frames, ignore_index=True).dropna()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.upper()
    df = df[(df["text"] != "") & (df["label"].isin(LABELS))]
    df = df.drop_duplicates(subset=["text"])
    counts = df["label"].value_counts()
    absent = [lab for lab in LABELS if counts.get(lab, 0) < 5]
    if absent:
        raise ValueError(f"Need at least 5 examples of each label; too few for: {', '.join(absent)}")
    return df.reset_index(drop=True)


def train_and_evaluate(data_paths, probe_path=None, seed: int = 42):
    """Train on 80%, evaluate on the held-out 20% and on an optional hand-written
    probe set, then refit on all data for the saved model. Returns (pipeline, metrics)."""
    df = load_dataset(data_paths)
    x_train, x_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, stratify=df["label"], random_state=seed
    )
    pipe = build_pipeline()
    pipe.fit(x_train, y_train)
    y_pred = pipe.predict(x_test)

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    metrics = {
        "n_samples": int(len(df)),
        "label_counts": {k: int(v) for k, v in df["label"].value_counts().items()},
        "test_accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "test_macro_f1": round(float(f1_score(y_test, y_pred, average="macro")), 4),
        "per_class": {
            k: {m: round(float(v), 4) for m, v in vals.items()} for k, vals in report.items() if k in LABELS
        },
        "confusion_matrix": {
            "labels": LABELS,
            "matrix": confusion_matrix(y_test, y_pred, labels=LABELS).tolist(),
        },
    }

    if probe_path and Path(probe_path).exists():
        probe = pd.read_csv(probe_path)
        probe.columns = [c.strip().lower() for c in probe.columns]
        probe["label"] = probe["label"].astype(str).str.strip().str.upper()
        p_pred = pipe.predict(probe["text"].astype(str))
        metrics["probe_accuracy"] = round(float(accuracy_score(probe["label"], p_pred)), 4)
        metrics["probe_size"] = int(len(probe))
        metrics["probe_errors"] = [
            {"text": t, "expected": e, "predicted": p}
            for t, e, p in zip(probe["text"], probe["label"], p_pred)
            if e != p
        ]

    final = build_pipeline()
    final.fit(df["text"], df["label"])
    return final, metrics


def save_model(pipe: Pipeline, metrics: dict, model_path, metrics_path) -> None:
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, model_path)
    Path(metrics_path).write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")


def load_model(model_path) -> Pipeline:
    return joblib.load(model_path)


def predict(pipe: Pipeline, texts: list[str]) -> list[Prediction]:
    if not texts:
        return []
    probs = pipe.predict_proba(list(texts))
    classes = list(pipe.classes_)
    out = []
    for row in probs:
        p = {c: float(v) for c, v in zip(classes, row)}
        label = classes[int(np.argmax(row))]
        risk = min(1.0, p.get("POSSIBLE_THREAT", 0.0) * 0.5 + p.get("THREAT", 0.0))
        out.append(Prediction(label=label, probs=p, risk=risk))
    return out
