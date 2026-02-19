"""
API маршруты для тестирования
"""
from fastapi import APIRouter
from datetime import datetime
from ...core.storage import storage
from ...services.websocket_service import websocket_service

router = APIRouter(prefix="/api/test", tags=["test"])


@router.post("/inject")
async def inject_test_data(data: dict = None):
    """
    Тестовый endpoint для инъекции данных
    
    Args:
        data: Тестовые данные (опционально)
        
    Returns:
        Статус и добавленные данные
    """
    if data is None:
        data = {
            "temperature": 22.5,
            "humidity": 45.0,
            "co2_ppm": 750.0,
            "co_ppm": 12.0,
            "lux": 320.0
        }
    
    storage.update_current_data(data)
    
    # Broadcast через WebSocket
    await websocket_service.broadcast(storage.current_data)
    
    return {
        "status": "success",
        "message": "Тестовые данные добавлены",
        "data": storage.current_data
    }
