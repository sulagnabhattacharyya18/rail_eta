"""Synthetic historical delay generation, calibrated to Indian Railways patterns."""
import random
import datetime as dt
from database import SessionLocal, Train, ScheduleStop, Station, HistoricalRun
from data.seed import ROUTES

NORTH_ZONES = {"NR", "NCR", "NWR"}

BASE_CONGESTION = {
    "NDLS": 8, "CNB": 5, "PRYJ": 4, "DDU": 4, "GAYA": 3, "DHN": 4,
    "ASN": 4, "HWH": 7, "CSMT": 6, "DR": 4, "TNA": 3, "LNL": 2,
    "PUNE": 4, "AGC": 3, "GWL": 3, "JHS": 4, "BPL": 4, "NGP": 4,
    "SUR": 3, "KJM": 3, "SBC": 5, "MAS": 6, "MMCT": 6, "BRC": 3,
    "RTM": 3, "KOTA": 3, "SDAH": 6, "BPQ": 3,
}

RECOVERY_RATE = {1: 0.80, 2: 0.70, 3: 0.60, 4: 0.50}


def weather_flags(date: dt.date, zone: str, hour: int):
    month = date.month
    fog = int(month in (12, 1, 2) and zone in NORTH_ZONES and 4 <= hour <= 10)
    rain = int(month in (7, 8, 9))
    return fog, rain


def congestion_penalty(station: str, hour: int) -> float:
    base = BASE_CONGESTION.get(station, 2)
    peak = 1.8 if hour in (8, 9, 10, 17, 18, 19) else 1.0
    return base * peak * random.uniform(0.8, 1.2) * 0.8


def evolve_delay(current_delay, sched_run, min_run, target_station,
                 target_hour, zone, run_date, priority, incident_extra=0.0):
    slack = max(sched_run - min_run, 0)
    recovery = min(max(current_delay, 0), slack * RECOVERY_RATE.get(priority, 0.5))
    recovery *= random.uniform(0.5, 1.0)

    cong = congestion_penalty(target_station, target_hour)
    fog, rain = weather_flags(run_date, zone, target_hour)
    weather = (random.uniform(10, 35) if fog else 0.0) + (random.uniform(5, 20) if rain else 0.0)
    noise = random.gauss(0, 1.5)

    new_delay = current_delay - recovery + cong + weather + incident_extra + noise
    return max(-5.0, new_delay)


def generate_historical_runs(days: int = 90, seed: int = 42):
    random.seed(seed)
    db = SessionLocal()
    try:
        if db.query(HistoricalRun).count() > 0:
            return
        trains = {t.train_no: t for t in db.query(Train).all()}
        sched_by_train = {}
        for s in db.query(ScheduleStop).order_by(ScheduleStop.train_no, ScheduleStop.seq).all():
            sched_by_train.setdefault(s.train_no, []).append(s)
        zones = {st.code: st.zone for st in db.query(Station).all()}

        today = dt.date.today()
        rows = []
        for offset in range(days):
            date = today - dt.timedelta(days=offset)
            for train_no, stops in sched_by_train.items():
                tr = trains[train_no]
                run_id = f"{train_no}_{date.isoformat()}"
                delay = 0.0
                for i, stop in enumerate(stops):
                    if i > 0:
                        prev = stops[i - 1]
                        sched_run = stop.arrival_min - prev.departure_min
                        hour = int((stop.arrival_min % 1440) // 60)
                        incident = 0.0
                        if random.random() < 0.08:
                            incident = random.choice([20, 40, 60, 90, 120])
                        delay = evolve_delay(
                            delay, sched_run, stop.min_run_from_prev,
                            stop.station_code, hour, zones[stop.station_code],
                            date, tr.priority, incident,
                        )
                    fog, rain = weather_flags(
                        date, zones[stop.station_code],
                        int((stop.arrival_min % 1440) // 60),
                    )
                    actual = stop.arrival_min + delay
                    rows.append(dict(
                        run_id=run_id, train_no=train_no, date=date,
                        station_code=stop.station_code, seq=stop.seq,
                        scheduled_arrival=stop.arrival_min,
                        actual_arrival=actual, delay=delay, fog=fog, rain=rain,
                    ))
        db.bulk_insert_mappings(HistoricalRun, rows)
        db.commit()
        print(f"[synthetic] Inserted {len(rows):,} historical rows across {days} days.")
    finally:
        db.close()