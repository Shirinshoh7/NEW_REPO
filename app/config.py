"""
Конфигурация приложения
Загрузка настроек из .env файла
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # MQTT
    MQTT_HOST: str
    MQTT_PORT: int = 8883
    MQTT_USER: str
    MQTT_PASSWORD: str
    MQTT_TOPIC: str = "iot/microclimate/data"
    
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    # Application
    APP_NAME: str = "MicroClimate AI Pro Backend"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Глобальный экземпляр настроек
settings = Settings()
