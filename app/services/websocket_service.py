"""
WebSocket сервис для real-time обновлений
"""
from typing import Dict
from ..core.storage import storage


class WebSocketService:
    """Сервис для WebSocket"""
    
    async def broadcast(self, data: Dict):
        """
        Рассылка данных всем WebSocket клиентам
        
        Args:
            data: Данные для отправки
        """
        disconnected = []
        
        for websocket in storage.active_websockets:
            try:
                await websocket.send_json(data)
            except:
                disconnected.append(websocket)
        
        # Удаление отключенных клиентов
        for ws in disconnected:
            storage.remove_websocket(ws)


# Глобальный экземпляр сервиса
websocket_service = WebSocketService()
