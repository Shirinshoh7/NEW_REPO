"""
Хранилище данных в памяти
"""
from collections import deque
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import WebSocket
from .constants import MAX_HISTORY_SIZE, PROFILES


class DataStorage:
    """Глобальное хранилище данных"""
    
    def __init__(self):
        # Текущие данные
        self.current_data: Dict = {
            "temperature": 0.0,
            "humidity": 0.0,
            "co2_ppm": 0.0,
            "lux": 0.0,
            "timestamp": None,
            "device_id": None
        }
        
        # История
        self.data_history = deque(maxlen=MAX_HISTORY_SIZE)
        
        # WebSocket клиенты
        self.active_websockets: List[WebSocket] = []
        
        # Активный профиль
        self.active_profile = PROFILES[0]
    
    def update_current_data(self, data: Dict):
        """Обновить текущие данные"""
        self.current_data = {
            "temperature": float(data.get("temperature", 0)),
            "humidity": float(data.get("humidity", 0)),
            "co2_ppm": float(data.get("co2_ppm", 0)),
            "lux": float(data.get("lux", 0)),
            "timestamp": datetime.now().isoformat(),
            "device_id": data.get("device_id", "esp32_main")
        }
        
        # Добавить в историю
        self.data_history.append({
            "temp": self.current_data["temperature"],
            "hum": self.current_data["humidity"],
            "co2": self.current_data["co2_ppm"],
            "lux": self.current_data["lux"],
            "time": datetime.now()
        })
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Получить историю"""
        limit = min(limit, MAX_HISTORY_SIZE)
        return list(self.data_history)[-limit:]
    
    def add_websocket(self, websocket: WebSocket):
        """Добавить WebSocket клиента"""
        self.active_websockets.append(websocket)
    
    def remove_websocket(self, websocket: WebSocket):
        """Удалить WebSocket клиента"""
        if websocket in self.active_websockets:
            self.active_websockets.remove(websocket)
    
    def update_profile(self, profile: Dict):
        """Обновить активный профиль"""
        self.active_profile = profile


# Глобальный экземпляр хранилища
storage = DataStorage()
