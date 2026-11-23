"""Inference: predict remaining-station ETAs with uncertainty bands."""
import datetime as dt
import joblib
import pandas as pd
from config import MODEL_PATH
from data.features import NUM_COLS, CAT_COLS, make_feature_row


def load_artifact():
    return joblib.load(MODEL_PATH)


def fmt_time(minutes):
    m = int(round(minutes))
    day = m // 1440 + 1
    rem = m % 1440
    hh, mm = rem // 60, rem % 60
    prefix = f"Day {day} " if day > 1 else ""
    return f"{prefix}{hh:02d}:{mm:02d}"


def predict_for_run(train_no, current_seq, current_delay, prev_delay,
                    run_date, art=None):
    art = art or load_artifact()
    sched = art["sched_by_train"][train_no]
    meta = art["train_meta"][train_no]
    stats, shc = art["stats"], art["shc"]

    rows = []
    for j in range(current_seq + 1, len(sched)):
        f = make_feature_row(
            train_no, meta, run_date, current_seq, j,
            current_delay, prev_delay,
            sched[current_seq], sched[j], sched, stats, shc,
        )
        X = pd.DataFrame([f])
        for c in NUM_COLS:
            X[c] = X[c].fillna(art["medians"][c])
        for c in CAT_COLS:
            X[c + "_enc"] = X[c].astype(str).map(
                art["cat_maps"][c]
            ).fillna(len(art["cat_maps"][c])).astype(int)
        X = X[art["feat_cols"]]

        q10 = float(art["models"][0.1].predict(X)[0])
        q50 = float(art["models"][0.5].predict(X)[0])
        q90 = float(art["models"][0.9].predict(X)[0])

        sched_arr = sched[j]["arrival_min"]
        rows.append({
            "seq": j,
            "station_code": sched[j]["station_code"],
            "distance_km": sched[j]["distance_km"],
            "scheduled_arrival_min": sched_arr,
            "scheduled_arrival": fmt_time(sched_arr),
            "baseline_delay": round(current_delay, 1),
            "baseline_eta_min": sched_arr + current_delay,
            "baseline_eta": fmt_time(sched_arr + current_delay),
            "pred_delay": round(q50, 1),
            "pred_eta_min": sched_arr + q50,
            "pred_eta": fmt_time(sched_arr + q50),
            "lower_delay": round(q10, 1),
            "upper_delay": round(q90, 1),
            "lower_eta_min": sched_arr + q10,
            "upper_eta_min": sched_arr + q90,
            "lower_eta": fmt_time(sched_arr + q10),
            "upper_eta": fmt_time(sched_arr + q90),
        })
    return rows