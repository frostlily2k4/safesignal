"""Train the SafeSignal message classifier and save it to models/.

Usage:
    python train.py
Trains on every CSV in data/ (except probe_set.csv), prints metrics, and
writes models/classifier.joblib and models/metrics.json.
"""
import json

from config import METRICS_PATH, MODEL_PATH, PROBE_PATH, training_files
from modules.classifier import save_model, train_and_evaluate


def main() -> None:
    files = training_files()
    print("Training files:", ", ".join(p.name for p in files) or "none")
    pipe, metrics = train_and_evaluate(files, PROBE_PATH)
    save_model(pipe, metrics, MODEL_PATH, METRICS_PATH)
    summary = {k: metrics[k] for k in ("n_samples", "label_counts", "test_accuracy", "test_macro_f1")}
    if "probe_accuracy" in metrics:
        summary["probe_accuracy"] = metrics["probe_accuracy"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    for err in metrics.get("probe_errors", []):
        print(f"  probe miss: expected {err['expected']:<16} got {err['predicted']:<16} | {err['text']}")
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
