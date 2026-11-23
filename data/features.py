

"""Feature engineering for ETA prediction. Used by both training and serving."""
import datetime as dt
import numpy as np
import pandas as pd
from data.synthetic import weather_flags

NUM_COLS = [
    "current_delay", "seq_ahead", "sched_run_min", "min_run_min",
    "recovery_slack_min", "recovery_ratio", "distance_ahead", "sched_speed",
    "target_hour", "target_dow", "is_weekend", "is_peak",
    "fog", "rain", "congestion", "train_priority",
    "delay_trend", "hist_train_station_mean_delay",
    "avg_delta_per_segment", "sched_dwell", "distance_from_origin",
    "remaining_ratio",
]
CAT_COLS = ["train_type", "zone", "current_zone"]





def schedule_to_dicts(stops):
    return [
        {
            "seq": s.seq, "station_code": s.station_code,
            "arrival_min": s.arrival_min, "departure_min": s.departure_min,
            "distance_km": s.distance_km, "halt_min": s.halt_min,
            "min_run_from_prev": s.min_run_from_prev,
        }
        for s in stops
    ]


def station_hour_counts(schedule_rows):
    """Count scheduled arrivals per station per hour — a static congestion proxy."""
    counts = {}
    for row in schedule_rows:
        hour = int((row["arrival_min"] % 1440) // 60)
        key = (row["station_code"], hour)
        counts[key] = counts.get(key, 0) + 1
    return counts


def compute_stats(hist_df: pd.DataFrame):
    global_mean = float(hist_df["delay"].mean())
    train_station = (
        hist_df.groupby(["train_no", "station_code"])["delay"].mean().to_dict()
    )
    hs = hist_df.sort_values(["run_id", "seq"]).copy()
    hs["prev_delay"] = hs.groupby("run_id")["delay"].shift(1)
    hs["delta"] = hs["delay"] - hs["prev_delay"]
    train_delta = hs.groupby("train_no")["delta"].mean().to_dict()
    return {
        "global_mean": global_mean,
        "train_station_delay": train_station,
        "train_avg_delta": train_delta,
    }


def make_feature_row(train_no, train_meta, date, k, j, current_delay,
                     prev_delay, sched_k, sched_j, sched_stops,
                     stats, shc):
    sched_run = sched_j["arrival_min"] - sched_k["departure_min"]
    min_run_total = sum(
        s["min_run_from_prev"] for s in sched_stops[k + 1:j + 1]
    )
    dist = sched_j["distance_km"] - sched_k["distance_km"]
    target_hour = int((sched_j["arrival_min"] % 1440) // 60)
    dow = date.weekday()
    zone = train_meta["zone_map"].get(sched_j["station_code"], "NR")
    cur_zone = train_meta["zone_map"].get(sched_k["station_code"], "NR")
    fog, rain = weather_flags(date, zone, target_hour)
    total_stops = len(sched_stops)

    return {
        "current_delay": float(current_delay),
        "seq_ahead": j - k,
        "sched_run_min": float(sched_run),
        "min_run_min": float(min_run_total),
        "recovery_slack_min": float(sched_run - min_run_total),
        "recovery_ratio": float((sched_run - min_run_total) / max(sched_run, 1)),
        "distance_ahead": float(dist),
        "sched_speed": float(dist / (sched_run / 60)) if sched_run > 0 else 0.0,
        "target_hour": target_hour,
        "target_dow": dow,
        "is_weekend": int(dow >= 5),
        "is_peak": int(target_hour in (8, 9, 10, 17, 18, 19)),
        "fog": fog,
        "rain": rain,
        "congestion": shc.get((sched_j["station_code"], target_hour), 1),
        "train_priority": train_meta["priority"],
        "delay_trend": float(current_delay - prev_delay),
        "hist_train_station_mean_delay": float(
            stats["train_station_delay"].get(
                (train_no, sched_j["station_code"]), stats["global_mean"]
            )
        ),
        "avg_delta_per_segment": float(stats["train_avg_delta"].get(train_no, 0.0)),
        "sched_dwell": float(sched_j["halt_min"]),
        "distance_from_origin": float(sched_j["distance_km"]),
        "remaining_ratio": float((j - k) / max(total_stops - k, 1)),
        "train_type": train_meta["train_type"],
        "zone": zone,
        "current_zone": cur_zone,
    }


def build_samples(hist_df, train_sched, train_meta, stats, shc,
                  max_k_per_run=4, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for run_id, g in hist_df.groupby("run_id"):
        g = g.sort_values("seq").reset_index(drop=True)
        n = len(g)
        if n < 3:
            continue
        train_no = g.loc[0, "train_no"]
        date = g.loc[0, "date"]
        if isinstance(date, pd.Timestamp):
            date = date.date()
        sched = train_sched[train_no]
        ks = rng.choice(range(1, n - 1), size=min(max_k_per_run, n - 2), replace=False)
        for k in sorted(ks):
            cur = g.loc[k]
            prev_delay = float(g.loc[k - 1, "delay"]) if k > 0 else float(cur["delay"])
            for j in range(k + 1, n):
                tgt = g.loc[j]
                row = make_feature_row(
    train_no, train_meta[train_no], date, int(k), int(j),
    float(cur["delay"]), prev_delay,
    sched[int(k)], sched[int(j)], sched, stats, shc,

                )
                row["target"] = float(tgt["delay"])
                row["run_id"] = run_id
                row["k"] = int(k)
                row["j"] = int(j)
                rows.append(row)
    return pd.DataFrame(rows)