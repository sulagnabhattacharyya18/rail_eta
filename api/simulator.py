"""Live train simulation with station-level delay propagation."""
import threading
import random
import datetime as dt
from database import SessionLocal, ScheduleStop, Station, Train, LivePosition
from data.synthetic import evolve_delay


class Simulator:
    def __init__(self):
        self.active = {}
        self.lock = threading.Lock()
        self._load_static()

    def _load_static(self):
        db = SessionLocal()
        try:
            self.zones = {s.code: s.zone for s in db.query(Station).all()}
            self.trains = {t.train_no: t for t in db.query(Train).all()}
            self.sched = {}
            for s in db.query(ScheduleStop).order_by(
                ScheduleStop.train_no, ScheduleStop.seq
            ).all():
                self.sched.setdefault(s.train_no, []).append({
                    "seq": s.seq, "station_code": s.station_code,
                    "arrival_min": s.arrival_min,
                    "departure_min": s.departure_min,
                    "distance_km": s.distance_km,
                    "halt_min": s.halt_min,
                    "min_run_from_prev": s.min_run_from_prev,
                })
        finally:
            db.close()

    def start(self, train_no):
        with self.lock:
            today = dt.date.today()
            self.active[train_no] = {
                "train_no": train_no,
                "run_date": today,
                "status": "AT_STATION",
                "current_seq": 0,
                "current_delay": 0.0,
                "prev_delay": 0.0,
                "next_delay": 0.0,
                "incident": 0.0,
                "last_update": dt.datetime.utcnow().isoformat(),
            }
            self._write_live(train_no)
            return self.state(train_no)

    def tick(self):
        with self.lock:
            for train_no in list(self.active):
                st = self.active[train_no]
                if st["status"] == "COMPLETED":
                    continue
                sched = self.sched[train_no]
                if st["status"] == "AT_STATION":
                    k = st["current_seq"]
                    if k >= len(sched) - 1:
                        st["status"] = "COMPLETED"
                        continue
                    nxt = sched[k + 1]
                    tr = self.trains[train_no]
                    hour = int((nxt["arrival_min"] % 1440) // 60)
                    sched_run = nxt["arrival_min"] - sched[k]["departure_min"]
                    inc = st.pop("incident", 0.0)
                    st["next_delay"] = evolve_delay(
                        st["current_delay"], sched_run,
                        nxt["min_run_from_prev"], nxt["station_code"],
                        hour, self.zones[nxt["station_code"]],
                        st["run_date"], tr.priority, inc,
                    )
                    st["status"] = "IN_TRANSIT"
                elif st["status"] == "IN_TRANSIT":
                    st["prev_delay"] = st["current_delay"]
                    st["current_delay"] = st["next_delay"]
                    st["current_seq"] += 1
                    st["status"] = "AT_STATION"
                    if st["current_seq"] >= len(sched) - 1:
                        st["status"] = "COMPLETED"
                    self._write_live(train_no)
                st["last_update"] = dt.datetime.utcnow().isoformat()

    def inject_incident(self, train_no, minutes=60):
        with self.lock:
            if train_no in self.active:
                self.active[train_no]["incident"] = (
                    self.active[train_no].get("incident", 0) + minutes
                )

    def _write_live(self, train_no):
        st = self.active[train_no]
        sched = self.sched[train_no]
        k = st["current_seq"]
        nxt = sched[k + 1] if k + 1 < len(sched) else None
        db = SessionLocal()
        try:
            db.add(LivePosition(
                train_no=train_no,
                timestamp=dt.datetime.utcnow(),
                status=st["status"],
                current_seq=k,
                current_station=sched[k]["station_code"],
                current_delay=st["current_delay"],
                next_station=nxt["station_code"] if nxt else None,
                next_eta_min=(nxt["arrival_min"] + st["current_delay"]) if nxt else None,
            ))
            db.commit()
        finally:
            db.close()

    def state(self, train_no):
        st = dict(self.active[train_no])
        sched = self.sched[train_no]
        k = st["current_seq"]
        st["current_station"] = sched[k]["station_code"]
        st["next_station"] = sched[k + 1]["station_code"] if k + 1 < len(sched) else None
        st["total_stops"] = len(sched)
        return st

    def all_states(self):
        return [self.state(t) for t in self.active]


SIM = Simulator()
