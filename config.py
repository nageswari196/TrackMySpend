"""
Central configuration for TrackMySpend.
All secrets / machine-specific paths are pulled from environment variables
(loaded from a local .env file if present) so the app is portable across
Windows / Mac / Linux and safe to deploy without editing source code.
"""
import os
import shutil
from dotenv import load_dotenv

load_dotenv()  # reads .env in project root if present

# --- Database ---
DB_FILE = os.getenv("DB_FILE", "expenses.db")

# --- Tesseract OCR ---
# Priority: explicit env var > auto-detect on PATH > common Windows install path
_env_tess = os.getenv("TESSERACT_CMD")
_auto_tess = shutil.which("tesseract")
DEFAULT_WIN_TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if _env_tess:
    TESSERACT_CMD = _env_tess
elif _auto_tess:
    TESSERACT_CMD = _auto_tess
elif os.path.exists(DEFAULT_WIN_TESS):
    TESSERACT_CMD = DEFAULT_WIN_TESS
else:
    TESSERACT_CMD = None  # OCR features will be disabled gracefully

# --- Currency conversion ---
# Free, keyless API. Falls back to static rates if unreachable.
EXCHANGE_RATE_API = "https://api.exchangerate.host/latest"
FALLBACK_RATES_TO_INR = {"USD": 83.0, "EUR": 90.0, "GBP": 105.0}

# --- AI Assistant (optional real LLM backend) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # if unset, falls back to rule-based assistant

# --- App ---
APP_NAME = "TRACKMYSPEND"
BASE_CURRENCY = "INR"
