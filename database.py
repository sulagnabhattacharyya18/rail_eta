from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Station(Base):
    __tablename__ = "stations"
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    zone = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    platforms = Column(Integer, default=2)


class Train(Base):
    __tablename__ = "trains"
    train_no = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    train_type = Column(String, nullable=False)
    priority = Column(Integer, nullable=False)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)


class ScheduleStop(Base):
    __tablename__ = "schedule"
    id = Column(Integer, primary_key=True)
    train_no = Column(String, ForeignKey("trains.train_no"), nullable=False)
    seq = Column(Integer, nullable=False)
    station_code = Column(String, ForeignKey("stations.code"), nullable=False)
    arrival_min = Column(Float, nullable=False)
    departure_min = Column(Float, nullable=False)
    distance_km = Column(Float, nullable=False)
    halt_min = Column(Float, nullable=False, default=0)
    min_run_from_prev = Column(Float, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("train_no", "seq", name="uq_train_seq"),)


class HistoricalRun(Base):
    __tablename__ = "historical_runs"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, nullable=False, index=True)
    train_no = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False)
    station_code = Column(String, nullable=False)
    seq = Column(Integer, nullable=False)
    scheduled_arrival = Column(Float, nullable=False)
    actual_arrival = Column(Float, nullable=False)
    delay = Column(Float, nullable=False)
    fog = Column(Integer, default=0)
    rain = Column(Integer, default=0)


class LivePosition(Base):
    __tablename__ = "live_positions"
    id = Column(Integer, primary_key=True)
    train_no = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    current_seq = Column(Integer, nullable=False)
    current_station = Column(String, nullable=False)
    current_delay = Column(Float, nullable=False)
    next_station = Column(String, nullable=True)
    next_eta_min = Column(Float, nullable=True)