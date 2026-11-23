"""Static network data: stations, trains, schedules."""
from database import Base, engine, SessionLocal, Station, Train, ScheduleStop

STATIONS = {
    # code: (name, zone, lat, lon, platforms)
    "NDLS": ("New Delhi",       "NR",  28.643, 77.219, 16),
    "CNB":  ("Kanpur Central",  "NCR", 26.449, 80.331, 10),
    "PRYJ": ("Prayagraj Jn",    "NCR", 25.440, 81.825, 8),
    "DDU":  ("Pt. DDU Jn",      "ECR", 25.282, 83.118, 8),
    "GAYA": ("Gaya Jn",         "ECR", 24.796, 85.000, 6),
    "DHN":  ("Dhanbad Jn",      "ECR", 23.795, 86.430, 6),
    "ASN":  ("Asansol Jn",      "ER",  23.684, 86.949, 6),
    "HWH":  ("Howrah Jn",       "ER",  22.583, 88.342, 23),
    "CSMT": ("Mumbai CSMT",     "CR",  18.940, 72.835, 18),
    "DR":   ("Dadar",           "CR",  19.018, 72.842, 8),
    "TNA":  ("Thane",           "CR",  19.186, 72.975, 8),
    "LNL":  ("Lonavala",        "CR",  18.750, 73.410, 4),
    "PUNE": ("Pune Jn",         "CR",  18.529, 73.874, 6),
    "AGC":  ("Agra Cantt",      "NCR", 27.159, 78.017, 6),
    "GWL":  ("Gwalior",         "NCR", 26.218, 78.183, 6),
    "JHS":  ("Jhansi Jn",       "NCR", 25.448, 78.570, 8),
    "BPL":  ("Bhopal Jn",       "WCR", 23.268, 77.402, 6),
    "NGP":  ("Nagpur Jn",       "CR",  21.153, 79.088, 8),
    "SUR":  ("Solapur Jn",      "CR",  17.660, 75.900, 5),
    "KJM":  ("Krishnarajapuram","SWR", 12.980, 77.620, 4),
    "SBC":  ("KSR Bengaluru",   "SWR", 12.978, 77.570, 10),
    "MAS":  ("Chennai Central", "SR",  13.083, 80.275, 12),
    "MMCT": ("Mumbai Central",  "WR",  18.971, 72.819, 8),
    "BRC":  ("Vadodara Jn",     "WR",  22.310, 73.180, 6),
    "RTM":  ("Ratlam Jn",       "WR",  23.330, 75.040, 6),
    "KOTA": ("Kota Jn",         "WCR", 25.180, 75.840, 6),
    "SDAH": ("Sealdah",         "ER",  22.567, 88.370, 20),
    "BPQ":  ("Balharshah Jn",   "CR",  19.830, 79.350, 5),
}

# train_no: (name, type, priority, stops)
# stop = (station_code, cumulative_km, min_run_from_prev_min, dwell_min)
ROUTES = {
    "12301": ("Howrah Rajdhani Express", "RAJDHANI", 1, [
        ("NDLS", 0, 0, 0), ("CNB", 440, 250, 5), ("PRYJ", 634, 120, 5),
        ("DDU", 990, 200, 5), ("GAYA", 1150, 100, 5), ("DHN", 1300, 90, 5),
        ("ASN", 1370, 40, 5), ("HWH", 1450, 55, 0),
    ]),
    "12302": ("New Delhi Rajdhani Express", "RAJDHANI", 1, [
        ("HWH", 0, 0, 0), ("ASN", 80, 55, 5), ("DHN", 150, 40, 5),
        ("GAYA", 300, 90, 5), ("DDU", 460, 100, 5), ("PRYJ", 816, 200, 5),
        ("CNB", 1010, 120, 5), ("NDLS", 1450, 250, 0),
    ]),
    "12123": ("Deccan Queen", "SUPERFAST", 3, [
        ("CSMT", 0, 0, 0), ("DR", 9, 12, 2), ("TNA", 34, 25, 2),
        ("LNL", 128, 75, 2), ("PUNE", 192, 65, 0),
    ]),
    "12627": ("Karnataka Express", "SUPERFAST", 3, [
        ("NDLS", 0, 0, 0), ("AGC", 195, 130, 5), ("GWL", 305, 80, 5),
        ("JHS", 415, 90, 5), ("BPL", 700, 230, 10), ("NGP", 1090, 280, 10),
        ("SUR", 1500, 300, 10), ("KJM", 2100, 420, 10), ("SBC", 2150, 40, 0),
    ]),
    "12615": ("Grand Trunk Express", "MAIL_EXPRESS", 4, [
        ("NDLS", 0, 0, 0), ("AGC", 195, 140, 5), ("GWL", 305, 90, 5),
        ("JHS", 415, 100, 5), ("BPL", 700, 250, 10), ("NGP", 1090, 300, 10),
        ("BPQ", 1350, 220, 10), ("MAS", 2175, 600, 0),
    ]),
    "12002": ("Bhopal Shatabdi", "SHATABDI", 1, [
        ("NDLS", 0, 0, 0), ("AGC", 195, 110, 5), ("GWL", 305, 75, 5),
        ("JHS", 415, 80, 5), ("BPL", 700, 180, 0),
    ]),
    "12951": ("Mumbai Rajdhani", "RAJDHANI", 1, [
        ("MMCT", 0, 0, 0), ("BRC", 392, 220, 5), ("RTM", 654, 150, 5),
        ("KOTA", 920, 160, 5), ("NDLS", 1380, 250, 0),
    ]),
    "12259": ("Sealdah Duronto", "DURONTO", 2, [
        ("SDAH", 0, 0, 0), ("ASN", 200, 140, 5), ("DHN", 260, 40, 5),
        ("GAYA", 400, 90, 5), ("DDU", 650, 150, 5), ("PRYJ", 1000, 220, 5),
        ("CNB", 1190, 120, 5), ("NDLS", 1630, 260, 0),
    ]),
}


def seed_if_empty():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Station).count() > 0:
            return
        for code, (name, zone, lat, lon, pf) in STATIONS.items():
            db.add(Station(code=code, name=name, zone=zone, lat=lat, lon=lon, platforms=pf))
        db.flush()

        for train_no, (name, ttype, priority, stops) in ROUTES.items():
            db.add(Train(
                train_no=train_no, name=name, train_type=ttype,
                priority=priority, source=stops[0][0], destination=stops[-1][0],
            ))
            db.flush()

            arrival = 0.0
            departure = 0.0
            for seq, (stn, km, min_run, dwell) in enumerate(stops):
                if seq > 0:
                    sched_run = round(min_run * 1.18)  # 18% schedule slack
                    arrival = departure + sched_run
                    departure = arrival + dwell
                db.add(ScheduleStop(
                    train_no=train_no, seq=seq, station_code=stn,
                    arrival_min=arrival, departure_min=departure,
                    distance_km=km, halt_min=dwell,
                    min_run_from_prev=min_run,
                ))
        db.commit()
        print("[seed] Network data inserted.")
    finally:
        db.close()