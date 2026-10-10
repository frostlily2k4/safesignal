import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def model():
    import config
    from modules.classifier import train_and_evaluate

    pipe, _ = train_and_evaluate(config.training_files(), config.PROBE_PATH)
    return pipe
