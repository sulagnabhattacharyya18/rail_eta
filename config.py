from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "artifacts"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "rail_eta.db"
MODEL_PATH = DATA_DIR / "eta_model.joblib"
BACKTEST_PATH = DATA_DIR / "backtest.json"
MINUTES_PER_DAY = 1440