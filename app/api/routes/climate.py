"""
API маршруты для климатических данных
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...core.storage import storage
from ...services.ai_service import ai_service
from ...services.websocket_service import websocket_service

router = APIRouter(prefix="/api", tags=["climate"])

SUPPORTED_HORIZONS_MIN = {
    "30m": 30,
    "3h": 180,
    "24h": 1440,
}
SAMPLE_PERIOD_MIN = 5


@router.get("/now")
async def get_current_data(forecast: str = "30m", forecast_min: int | None = None):
    """
    Получение текущих данных с AI прогнозом
    
    Args:
        forecast: Горизонт прогноза ("30m", "3h", "24h")
        forecast_min: Время прогноза в минутах (приоритетнее forecast)
        
    Returns:
        Текущие данные и прогнозы
    """
    if storage.current_data["timestamp"] is None:
        return {
            "error": "no_data",
            "message": "Нет данных от ESP32. Проверьте MQTT."
        }
    
    # Определение горизонта прогноза
    if forecast_min is not None:
        target_minutes = max(1, int(forecast_min))
    else:
        target_minutes = SUPPORTED_HORIZONS_MIN.get(forecast, 30)

    steps_ahead = max(1, round(target_minutes / SAMPLE_PERIOD_MIN))

    # AI прогноз для всех параметров
    temp_history = [float(d.get("temp", d.get("temperature", 0))) for d in storage.data_history]
    hum_history = [float(d.get("hum", d.get("humidity", 0))) for d in storage.data_history]
    co2_history = [float(d.get("co2", d.get("co2_ppm", 0))) for d in storage.data_history]
    co_history = [float(d.get("co", d.get("co_ppm", 0))) for d in storage.data_history]
    lux_history = [float(d.get("lux", 0)) for d in storage.data_history]
    
    predictions = {
        "temperature": ai_service.predict_linear(temp_history, steps_ahead),
        "humidity": ai_service.predict_linear(hum_history, steps_ahead),
        "co2": ai_service.predict_linear(co2_history, steps_ahead),
        "co": ai_service.predict_linear(co_history, steps_ahead),
        "lux": ai_service.predict_linear(lux_history, steps_ahead)
    }
    
    # MC Score
    mc_score = ai_service.calculate_mc_score(
        storage.current_data,
        storage.active_profile
    )
    
    return {
        "current": {
            "temp": storage.current_data["temperature"],
            "hum": storage.current_data["humidity"],
            "co2": storage.current_data["co2_ppm"],
            "co": storage.current_data["co_ppm"],
            "lux": storage.current_data["lux"],
            "mc_score": mc_score
        },
        "predictions": predictions,
        "forecast": {
            "label": forecast if forecast in SUPPORTED_HORIZONS_MIN else f"{target_minutes}m",
            "minutes": target_minutes,
            "steps_ahead": steps_ahead,
            "sample_period_min": SAMPLE_PERIOD_MIN,
        },
        "device_id": storage.current_data["device_id"],
        "timestamp": storage.current_data["timestamp"],
        "profile": storage.active_profile["name"]
    }


@router.get("/stats")
async def get_statistics():
    """Получение статистики по всем параметрам"""
    if len(storage.data_history) == 0:
        return {"error": "no_data"}
    
    temps = [float(d.get("temp", d.get("temperature", 0))) for d in storage.data_history]
    hums = [float(d.get("hum", d.get("humidity", 0))) for d in storage.data_history]
    co2s = [float(d.get("co2", d.get("co2_ppm", 0))) for d in storage.data_history]
    cos = [float(d.get("co", d.get("co_ppm", 0))) for d in storage.data_history]
    luxs = [float(d.get("lux", 0)) for d in storage.data_history]
    
    return {
        "measurements": len(storage.data_history),
        "temperature": {
            "current": storage.current_data["temperature"],
            "min": min(temps),
            "max": max(temps),
            "avg": round(sum(temps) / len(temps), 1)
        },
        "humidity": {
            "current": storage.current_data["humidity"],
            "min": min(hums),
            "max": max(hums),
            "avg": round(sum(hums) / len(hums), 1)
        },
        "co2": {
            "current": storage.current_data["co2_ppm"],
            "min": min(co2s),
            "max": max(co2s),
            "avg": round(sum(co2s) / len(co2s), 1)
        },
        "co": {
            "current": storage.current_data["co_ppm"],
            "min": min(cos),
            "max": max(cos),
            "avg": round(sum(cos) / len(cos), 1)
        },
        "lux": {
            "current": storage.current_data["lux"],
            "min": min(luxs),
            "max": max(luxs),
            "avg": round(sum(luxs) / len(luxs), 1)
        }
    }


@router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket для real-time обновлений
    """
    await websocket.accept()
    storage.add_websocket(websocket)
    
    client_id = id(websocket)
    print(f"✅ WebSocket [{client_id}] подключен. Всего: {len(storage.active_websockets)}")
    
    try:
        # Отправляем текущие данные сразу
        if storage.current_data["timestamp"]:
            await websocket.send_json(storage.current_data)
        
        # Держим соединение
        while True:
            try:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"❌ WebSocket [{client_id}] ошибка: {e}")
        
    finally:
        storage.remove_websocket(websocket)
        print(f"❌ WebSocket [{client_id}] отключен. Осталось: {len(storage.active_websockets)}")
