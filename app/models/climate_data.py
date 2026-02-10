"""
Pydantic модели для климатических данных
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClimateData(BaseModel):
    """Модель климатических данных"""
    temperature: float = Field(..., description="Температура в °C")
    humidity: float = Field(..., description="Влажность в %")
    co2_ppm: float = Field(..., description="CO2 в ppm")
    lux: float = Field(..., description="Освещенность в люксах")
    device_id: Optional[str] = Field("esp32_main", description="ID устройства")


class ClimateResponse(BaseModel):
    """Ответ с текущими данными"""
    current: dict
    predictions: dict
    device_id: str
    timestamp: str
    profile: str


class PredictionsData(BaseModel):
    """Модель прогнозов"""
    temperature: float
    humidity: float
    co2: float
    lux: float


class CurrentData(BaseModel):
    """Текущие данные с MC Score"""
    temp: float
    hum: float
    co2: float
    lux: float
    mc_score: int
