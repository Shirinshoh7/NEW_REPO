"""
Хранилище данных в памяти
"""
from collections import deque
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from fastapi import WebSocket
from .constants import MAX_HISTORY_SIZE, PROFILES


class DataStorage:
    """Глобальное хранилище данных"""

    def __init__(self):
        self._active_profile_path = Path("app/data/active_profile.json")
        self.current_data: Dict = {
            "temperature": 0.0,
            "humidity": 0.0,
            "co2_ppm": 0.0,
            "co_ppm": 0.0,
            "lux": 0.0,
            "timestamp": None,
            "device_id": None
        }

        self.data_history = deque(maxlen=MAX_HISTORY_SIZE)
        self.active_websockets: List[WebSocket] = []
        self.active_profile = self._load_active_profile()

    def _load_active_profile(self) -> Dict:
        """Загружает активный профиль из файла, если он есть."""
        try:
            if self._active_profile_path.exists():
                raw = self._active_profile_path.read_text(encoding="utf-8")
                profile = json.loads(raw)
                if isinstance(profile, dict):
                    base = dict(PROFILES[0])
                    base.update(profile)
                    return base
        except Exception as e:
            print(f"⚠️ Не удалось загрузить active_profile.json: {e}")
        return dict(PROFILES[0])

    def _save_active_profile(self) -> None:
        """Сохраняет активный профиль в файл."""
        try:
            self._active_profile_path.parent.mkdir(parents=True, exist_ok=True)
            self._active_profile_path.write_text(
                json.dumps(self.active_profile, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"⚠️ Не удалось сохранить active_profile.json: {e}")

    def _to_float(self, v, default=0.0) -> float:
        try:
            return float(v)
        except Exception:
            return default

    def _evaluate_norm(
        self,
        temperature: float,
        humidity: float,
        co2_ppm: float,
        co_ppm: float,
        lux: float,
    ) -> Dict:
        """Проверка 'норма/вне нормы' по активному профилю"""
        p = self.active_profile or {}
        issues = []

        tmin = p.get("temp_min")
        tmax = p.get("temp_max")
        if tmin is not None and temperature < tmin:
            issues.append("temperature")
        if tmax is not None and temperature > tmax:
            issues.append("temperature")

        hmax = p.get("humidity_max")
        if hmax is not None and humidity > hmax:
            issues.append("humidity")

        cmax = p.get("co2_max")
        if cmax is not None and co2_ppm > cmax:
            issues.append("co2_ppm")

        comax = p.get("co_max")
        if comax is not None and co_ppm > comax:
            issues.append("co_ppm")

        # lux может быть в профиле как lux_max/lux_min (если есть)
        lmin = p.get("lux_min")
        lmax = p.get("lux_max")
        if lmin is not None and lux < lmin:
            issues.append("lux")
        if lmax is not None and lux > lmax:
            issues.append("lux")

        is_danger = len(issues) > 0
        return {
            "is_danger": is_danger,
            "issues": list(sorted(set(issues))),
            "status": "out_of_range" if is_danger else "ok",
            "message": "Вне нормы" if is_danger else "Норма",
        }

    def update_current_data(self, data: Dict):
        """Обновить текущие данные"""
        temperature = self._to_float(data.get("temperature", 0))
        humidity = self._to_float(data.get("humidity", 0))
        co2_ppm = self._to_float(data.get("co2_ppm", 0))
        co_ppm = self._to_float(data.get("co_ppm", data.get("co", 0)))
        lux = self._to_float(data.get("lux", 0))

        now_iso = datetime.now().isoformat()

        self.current_data = {
            "temperature": temperature,
            "humidity": humidity,
            "co2_ppm": co2_ppm,
            "co_ppm": co_ppm,
            "lux": lux,
            "timestamp": now_iso,
            "device_id": data.get("device_id", "esp32_main")
        }

        norm = self._evaluate_norm(temperature, humidity, co2_ppm, co_ppm, lux)

        # ✅ Добавить в историю уже с "Норма/Вне нормы"
        self.data_history.append({
            "temp": temperature,
            "hum": humidity,
            "co2": co2_ppm,
            "co": co_ppm,
            "lux": lux,
            "time": now_iso,
            "profile": self.active_profile.get("name"),
            **norm
        })

    def get_history(self, limit: int = 50) -> List[Dict]:
        limit = min(limit, MAX_HISTORY_SIZE)
        return list(self.data_history)[-limit:]

    def add_websocket(self, websocket: WebSocket):
        self.active_websockets.append(websocket)

    def remove_websocket(self, websocket: WebSocket):
        if websocket in self.active_websockets:
            self.active_websockets.remove(websocket)

    def update_profile(self, profile: Dict):
        self.active_profile = dict(profile)
        self._save_active_profile()


storage = DataStorage()
