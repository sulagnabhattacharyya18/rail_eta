"""FastAPI backend for the ETA service."""
import os
import json
import threading
import time
import datetime as dt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, Train, ScheduleStop, Station
from config import MODEL_PATH, BACKTEST_PATH
from data.seed import seed_if_empty
from ml.train import train as train_model
from ml.predict import predict_for_run, load_artifact
from api.schemas import PredictResponse

app = FastAPI(
    title="Dynamic Train ETA Forecasting — SIH26028",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

ART = None
SIM = None

def bootstrap():
    global ART, SIM

    # First create database tables and insert static data
    seed_if_empty()

    # Initialize simulator only AFTER database initialization
    from api.simulator import SIM as simulator
    SIM = simulator

    # Train or load the prediction model
    if not MODEL_PATH.exists():
        train_model()

    ART = load_artifact()


@app.on_event("startup")
def on_startup():
    bootstrap()
    if os.getenv("AUTO_TICK", "0") == "1":
        def loop():
            while True:
                time.sleep(10)
                try:
                    SIM.tick()
                except Exception as e:
                    print("[sim]", e)
        threading.Thread(target=loop, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": ART is not None}


@app.get("/trains")
def list_trains():
    db = SessionLocal()
    try:
        return [
            {"train_no": t.train_no, "name": t.name,
             "type": t.train_type, "source": t.source,
             "destination": t.destination}
            for t in db.query(Train).all()
        ]
    finally:
        db.close()


@app.get("/schedule/{train_no}")
def get_schedule(train_no: str):
    db = SessionLocal()
    try:
        rows = db.query(ScheduleStop).filter(
            ScheduleStop.train_no == train_no
        ).order_by(ScheduleStop.seq).all()
        if not rows:
            raise HTTPException(404, "Train not found")
        stations = {s.code: s for s in db.query(Station).all()}
        return [
            {"seq": r.seq, "station": r.station_code,
             "station_name": stations[r.station_code].name,
             "arrival_min": r.arrival_min, "departure_min": r.departure_min,
             "distance_km": r.distance_km,
             "lat": stations[r.station_code].lat,
             "lon": stations[r.station_code].lon}
            for r in rows
        ]
    finally:
        db.close()


@app.post("/simulate/start/{train_no}")
def start_sim(train_no: str):
    if train_no not in SIM.sched:
        raise HTTPException(404, "Unknown train")
    return SIM.start(train_no)


@app.post("/simulate/tick")
def tick_sim():
    SIM.tick()
    return {"active": SIM.all_states()}


@app.post("/simulate/incident/{train_no}")
def incident(train_no: str, minutes: int = 60):
    if train_no not in SIM.active:
        raise HTTPException(400, "Start the simulation first")
    SIM.inject_incident(train_no, minutes)
    return {"train_no": train_no, "injected_minutes": minutes}


@app.get("/live")
def live_all():
    return SIM.all_states()


@app.get("/live/{train_no}")
def live_one(train_no: str):
    if train_no not in SIM.active:
        raise HTTPException(404, "Not running. POST /simulate/start/{train_no}")
    return SIM.state(train_no)


@app.get("/predict/{train_no}", response_model=PredictResponse)
def predict(train_no: str):
    if train_no not in SIM.active:
        SIM.start(train_no)
    st = SIM.state(train_no)
    if st["status"] == "COMPLETED":
        raise HTTPException(400, "Journey completed")
    preds = predict_for_run(
        train_no, st["current_seq"], st["current_delay"],
        st["prev_delay"], st["run_date"], ART,
    )
    db = SessionLocal()
    try:
        tr = db.query(Train).filter(Train.train_no == train_no).first()
        return {
            "train_no": train_no, "train_name": tr.name,
            "current_station": st["current_station"],
            "current_delay_min": round(st["current_delay"], 1),
            "status": st["status"],
            "predictions": preds,
        }
    finally:
        db.close()


@app.get("/backtest")
def backtest():
    if BACKTEST_PATH.exists():
        return json.loads(BACKTEST_PATH.read_text())
    return {"error": "No backtest found. Run training."}