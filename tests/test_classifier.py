import pandas as pd
import pytest

from modules.classifier import load_dataset, predict


def test_predict_shapes(model):
    preds = predict(model, ["see you at the library", "I will hurt you"])
    assert len(preds) == 2
    for p in preds:
        assert abs(sum(p.probs.values()) - 1) < 1e-6
        assert 0 <= p.risk <= 1
    assert preds[1].risk > preds[0].risk
    assert predict(model, []) == []


def test_load_dataset_validation(tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"message": ["x"], "label": ["SAFE"]}).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        load_dataset(bad)
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "missing.csv")
    few = tmp_path / "few.csv"
    pd.DataFrame({"text": ["a", "b"], "label": ["SAFE", "THREAT"]}).to_csv(few, index=False)
    with pytest.raises(ValueError):
        load_dataset(few)


def test_load_dataset_cleans_labels(tmp_path):
    f = tmp_path / "d.csv"
    rows = [(f"text {i} {lab}", f" {lab.lower()} ") for lab in ["SAFE", "POSSIBLE_THREAT", "THREAT"] for i in range(5)]
    rows += [("text 0 SAFE", "SAFE"), ("", "SAFE"), ("odd", "UNKNOWN")]
    pd.DataFrame(rows, columns=["text", "label"]).to_csv(f, index=False)
    df = load_dataset(f)
    assert len(df) == 15
    assert set(df["label"]) == {"SAFE", "POSSIBLE_THREAT", "THREAT"}
