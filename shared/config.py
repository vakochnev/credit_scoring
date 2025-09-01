from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
MODELS_DIR = ROOT_DIR / "models"
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"

FEATURE_NAMES_PATH = MODELS_DIR / "feature_names.pkl"
BACKGROUND_DATA_PATH = MODELS_DIR / "background_data.pkl"
ENSEMBLE_MODEL_PATH = MODELS_DIR / "ensemble_model.pkl"
REPORT_PATH = REPORTS_DIR / "explanation_report.pdf"

DATA_SOURCE = DATA_DIR / "credit_risk_dataset.csv"

API_BASE_URL = "http://localhost:8000"
HOST = "localhost"
PORT = 8000
API_AUTH = ("admin", "password123")

for path in [MODELS_DIR, REPORTS_DIR, DATA_DIR]:
    path.mkdir(exist_ok=True)