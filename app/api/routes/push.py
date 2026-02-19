from fastapi import APIRouter
from pydantic import BaseModel

from ...config import settings
from ...services.firebase_service import firebase_service

router = APIRouter(prefix="/api/push", tags=["push-notifications"])


class TokenRegister(BaseModel):
    user_id: str | None = None
    token: str
    platform: str = "android"


class TokenUnregister(BaseModel):
    user_id: str | None = None
    token: str


class PushTestRequest(BaseModel):
    user_id: str | None = None
    title: str = "Тестовое уведомление"
    body: str = "FCM работает корректно"


@router.post("/register")
async def register_token(data: TokenRegister):
    user_id = settings.FCM_DEFAULT_USER_ID
    total = firebase_service.register_token(user_id, data.token)
    return {"status": "registered", "user_id": user_id, "tokens": total, "platform": data.platform}


@router.post("/unregister")
async def unregister_token(data: TokenUnregister):
    user_id = settings.FCM_DEFAULT_USER_ID
    total = firebase_service.unregister_token(user_id, data.token)
    return {"status": "unregistered", "user_id": user_id, "tokens": total}


@router.post("/test")
async def send_test_push(data: PushTestRequest):
    user_id = settings.FCM_DEFAULT_USER_ID
    sent = firebase_service.send_push_to_user(
        user_id=user_id,
        title=data.title,
        body=data.body,
        data={"type": "manual_test"},
    )
    return {"status": "sent" if sent else "not_sent", "user_id": user_id}


@router.get("/stats")
async def push_stats():
    user_id = settings.FCM_DEFAULT_USER_ID
    return {
        "users": firebase_service.get_users_count(),
        "default_user_id": user_id,
        "default_user_tokens": firebase_service.get_tokens_count(user_id),
    }
