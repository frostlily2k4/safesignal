"""Central configuration for SafeSignal. Secrets come from environment
variables (.env locally) or Streamlit secrets (Streamlit Community Cloud)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional at runtime
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_PATH = DATA_DIR / "dataset.csv"
PROBE_PATH = BASE_DIR / "data" / "probe_set.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "classifier.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
SAMPLE_CHATS_DIR = BASE_DIR / "assets" / "sample_chats"


def training_files() -> list[Path]:
    """Every CSV in data/ except the probe set. Drop your own labelled CSV
    (columns: text,label) into data/ and it is included automatically."""
    return sorted(p for p in DATA_DIR.glob("*.csv") if p.name != PROBE_PATH.name)

LABELS = ["SAFE", "POSSIBLE_THREAT", "THREAT"]

# Risk thresholds on the 0-1 combined risk score
POSSIBLE_THRESHOLD = 0.35
THREAT_THRESHOLD = 0.65

# Escalation: rise in average risk between first and last third of a chat
ESCALATION_DELTA = 0.15

# Input limits (protect the app from huge uploads)
MAX_UPLOAD_BYTES = 2_000_000
MAX_MESSAGES = 3000
MAX_SINGLE_MESSAGE_CHARS = 2000

# How many flagged messages (redacted) may be sent to the LLM
MAX_LLM_EXCERPTS = 25


def get_setting(name: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets first, then environment."""
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def gemini_api_key() -> str:
    return get_setting("GEMINI_API_KEY", "").strip()


def gemini_model() -> str:
    return get_setting("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
