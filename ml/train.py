"""Train quantile ETA models and produce a held-out backtest."""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sqlalchemy import func
from database import SessionLocal, HistoricalRun, Train, Station, ScheduleStop
from config import MODEL_PATH, BACKTEST_PATH
from data.seed import seed_if_empty
from data.synthetic import generate_historical_runs
from data.features import (
    NUM_COLS, CAT_COLS, compute_stats, station_hour_counts,
    schedule_to_dicts, build_samples,
)


def load_data():
    db = SessionLocal()
    try:
        trains = {t.train_no: t for t in db.query(Train).all()}
        zones = {s.code: s.zone for s in db.query(Station).all()}
        train_meta = {
            tno: {
                "train_type": t.train_type, "priority": t.priority,
                "zone_map": zones,
            }
            for tno, t in trains.items()
        }
        sched_rows = []
        sched_by_train = {}
        for s in db.query(ScheduleStop).order_by(ScheduleStop.train_no, ScheduleStop.seq).all():
            d = dict(
                train_no=s.train_no, seq=s.seq, station_code=s.station_code,
                arrival_min=s.arrival_min, departure_min=s.departure_min,
                distance_km=s.distance_km, halt_min=s.halt_min,
                min_run_from_prev=s.min_run_from_prev,
            )
            sched_rows.append(d)
            sched_by_train.setdefault(s.train_no, []).append(d)

        hist = pd.read_sql(db.query(HistoricalRun).statement, db.bind)
        return train_meta, sched_by_train, sched_rows, hist
    finally:
        db.close()


def encode_cats(train_df, test_df, cat_maps=None):
    if cat_maps is None:
        cat_maps = {}
        for c in CAT_COLS:
            vals = sorted(train_df[c].astype(str).unique())
            cat_maps[c] = {v: i for i, v in enumerate(vals)}
    for df in (train_df, test_df):
        for c in CAT_COLS:
            df[c + "_enc"] = (
                df[c].astype(str).map(cat_maps[c]).fillna(len(cat_maps[c])).astype(int)
            )
    return cat_maps


def train():
    seed_if_empty()
    generate_historical_runs(days=90)

    train_meta, sched_by_train, sched_rows, hist = load_data()
    hist["date"] = pd.to_datetime(hist["date"])
    dates = sorted(hist["date"].unique())
    split_idx = int(len(dates) * 0.8)
    train_dates = set(dates[:split_idx])
    train_hist = hist[hist["date"].isin(train_dates)].copy()
    test_hist = hist[~hist["date"].isin(train_dates)].copy()

    stats = compute_stats(train_hist)
    shc = station_hour_counts(sched_rows)

    train_df = build_samples(train_hist, sched_by_train, train_meta, stats, shc)
    test_df = build_samples(test_hist, sched_by_train, train_meta, stats, shc, seed=99)

    cat_maps = encode_cats(train_df, test_df)

    medians = train_df[NUM_COLS].median()
    for df in (train_df, test_df):
        for c in NUM_COLS:
            df[c] = df[c].fillna(medians[c])

    feat_cols = NUM_COLS + [c + "_enc" for c in CAT_COLS]
    cat_idx = [feat_cols.index(c + "_enc") for c in CAT_COLS]

    X_train, y_train = train_df[feat_cols], train_df["target"]
    X_test, y_test = test_df[feat_cols], test_df["target"]

    models = {}
    for q in (0.1, 0.5, 0.9):
        m = HistGradientBoostingRegressor(
            loss="quantile", quantile=q, max_iter=500,
            learning_rate=0.05, max_depth=6, min_samples_leaf=10,
            random_state=42, categorical_features=cat_idx,
        )
        m.fit(X_train, y_train)
        models[q] = m

    pred = models[0.5].predict(X_test)
    lo = models[0.1].predict(X_test)
    hi = models[0.9].predict(X_test)
    baseline = X_test["current_delay"].values

    mae_model = float(np.mean(np.abs(pred - y_test)))
    mae_base = float(np.mean(np.abs(baseline - y_test)))
    coverage = float(np.mean((y_test >= lo) & (y_test <= hi)))
    improvement = float((mae_base - mae_model) / mae_base * 100)

    metrics = {
        "mae_baseline_min": round(mae_base, 2),
        "mae_model_min": round(mae_model, 2),
        "improvement_pct": round(improvement, 2),
        "interval_coverage_pct": round(coverage * 100, 2),
        "test_samples": int(len(y_test)),
        "baseline_name": "schedule + current delay",
        "model_name": "HistGradientBoosting quantile (q10/q50/q90)",
    }

    joblib.dump(
        {
            "models": models, "cat_maps": cat_maps, "medians": medians,
            "feat_cols": feat_cols, "stats": stats, "shc": shc,
            "train_meta": train_meta, "sched_by_train": sched_by_train,
        },
        MODEL_PATH,
    )
    BACKTEST_PATH.write_text(json.dumps(metrics, indent=2))
    print("[train] Saved model and backtest.")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    train()