# Dynamic Train Arrival Forecasting — SIH26028

A complete ETA prediction service for Indian Railways coaching trains.
Predicts arrival delay at every downstream station as a distribution,
using live position + delay, route history, congestion, weather and
scheduled recovery slack.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Terminal 1 — API (first run seeds data and trains the model, ~30 s)
uvicorn api.main:app --reload --port 8000

# Terminal 2 — dashboard
streamlit run dashboard/app.py