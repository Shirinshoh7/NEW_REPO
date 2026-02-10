"""
Модели климатических профилей
"""
from pydantic import BaseModel, Field


class Profile(BaseModel):
    """Модель профиля помещения"""
    name: str = Field(..., description="Название профиля")
    temp_min: float = Field(..., description="Минимальная температура")
    temp_max: float = Field(..., description="Максимальная температура")
    humidity_max: float = Field(..., description="Максимальная влажность")
    co2_max: float = Field(..., description="Максимальный CO2")
    lux_min: float = Field(..., description="Минимальная освещенность")
    lux_max: float = Field(..., description="Максимальная освещенность")


class ProfilesResponse(BaseModel):
    """Ответ со списком профилей"""
    presets: list
    active: dict
