"""
API маршруты для климатических данных
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...core.storage import storage
from ...services.ai_service import ai_service
from ...services.websocket_service import websocket_service

router = APIRouter(prefix="/api", tags=["climate"])


@router.get("/now")
async def get_current_data(forecast_min: int = 5):
    """
    Получение текущих данных с AI прогнозом
    
    Args:
        forecast_min: Время прогноза в минутах
        
    Returns:
        Текущие данные и прогнозы
    """
    if storage.current_data["timestamp"] is None:
        return {
            "error": "no_data",
            "message": "Нет данных от ESP32. Проверьте MQTT."
        }
    
    # AI прогноз для всех параметров
    temp_history = [d["temp"] for d in storage.data_history]
    hum_history = [d["hum"] for d in storage.data_history]
    co2_history = [d["co2"] for d in storage.data_history]
    lux_history = [d["lux"] for d in storage.data_history]
    
    predictions = {
        "temperature": ai_service.predict_linear(temp_history),
        "humidity": ai_service.predict_linear(hum_history),
        "co2": ai_service.predict_linear(co2_history),
        "lux": ai_service.predict_linear(lux_history)
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
            "lux": storage.current_data["lux"],
            "mc_score": mc_score
        },
        "predictions": predictions,
        "device_id": storage.current_data["device_id"],
        "timestamp": storage.current_data["timestamp"],
        "profile": storage.active_profile["name"]
    }


@router.get("/stats")
async def get_statistics():
    """Получение статистики по всем параметрам"""
    if len(storage.data_history) == 0:
        return {"error": "no_data"}
    
    temps = [d["temp"] for d in storage.data_history]
    hums = [d["hum"] for d in storage.data_history]
    co2s = [d["co2"] for d in storage.data_history]
    luxs = [d["lux"] for d in storage.data_history]
    
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
