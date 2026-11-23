from pydantic import BaseModel
from typing import List, Optional

class PredictionItem(BaseModel):
    seq: int
    station_code: str
    distance_km: float
    scheduled_arrival_min: float
    scheduled_arrival: str
    baseline_delay: float
    baseline_eta_min: float
    baseline_eta: str
    pred_delay: float
    pred_eta_min: float
    pred_eta: str
    lower_delay: float
    upper_delay: float
    lower_eta_min: float
    upper_eta_min: float

    lower_eta: str
    upper_eta: str

class PredictResponse(BaseModel):
    train_no: str
    train_name: str
    current_station: str
    current_delay_min: float
    status: str
    predictions: List[PredictionItem]