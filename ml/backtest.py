import json
from config import BACKTEST_PATH

def get_backtest():
    if BACKTEST_PATH.exists():
        return json.loads(BACKTEST_PATH.read_text())
    return {"error": "Run `python -m ml.train` first."}

if __name__ == "__main__":
    print(json.dumps(get_backtest(), indent=2))