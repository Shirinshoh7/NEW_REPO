"""
API маршруты для профилей
"""
from fastapi import APIRouter
from ...core.storage import storage
from ...core.constants import PROFILES
from ...models.profile import Profile

router = APIRouter(prefix="/api", tags=["profiles"])


@router.get("/profiles")
async def get_profiles():
    """Получение всех профилей"""
    return {
        "presets": PROFILES,
        "active": storage.active_profile
    }


@router.post("/profile/update")
async def update_profile(profile: dict):
    """
    Обновление активного профиля
    
    Args:
        profile: Данные нового профиля
        
    Returns:
        Статус операции
    """
    required = ["name", "temp_min", "temp_max", "humidity_max", "co2_max", "co_max", "lux_min", "lux_max"]
    
    for field in required:
        if field not in profile:
            return {
                "status": "error",
                "message": f"Отсутствует поле: {field}"
            }
    
    storage.update_profile(profile)
    
    return {
        "status": "success",
        "message": f"Профиль обновлен: {profile['name']}",
        "active_profile": storage.active_profile
    }
