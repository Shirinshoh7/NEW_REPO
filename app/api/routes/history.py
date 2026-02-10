"""
API маршруты для истории
"""
from fastapi import APIRouter
from ...core.storage import storage

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def get_history(limit: int = 50):
    """
    Получение истории измерений
    
    Args:
        limit: Максимальное количество записей
        
    Returns:
        История измерений
    """
    history_data = storage.get_history(limit)
    
    return {
        "count": len(history_data),
        "data": history_data
    }
