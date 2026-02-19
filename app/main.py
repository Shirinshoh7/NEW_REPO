"""
Главный файл FastAPI приложения
"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import settings
from .services.mqtt_service import mqtt_service
from .services.firebase_service import firebase_service
from .core.storage import storage

# Импорт роутеров
from .api.routes import climate, profiles, history, test, push


app = FastAPI(
    title=settings.APP_NAME,
    description="Real-Time IoT Backend с MQTT и WebSocket (5 параметров)",
    version=settings.APP_VERSION
)

# ✅ CORS для Flutter Web / Chrome (DEV)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # DEV: разрешить все домены
    allow_credentials=False,      # MUST be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Подключение роутеров
app.include_router(climate.router)
app.include_router(profiles.router)
app.include_router(history.router)
app.include_router(test.router)
app.include_router(push.router)


@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 70)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 70)

    # Инициализация Firebase/FCM
    firebase_service.init_firebase()

    # Настройка и запуск MQTT
    loop = asyncio.get_event_loop()
    mqtt_service.setup(loop)

    if mqtt_service.connect():
        print("✅ MQTT клиент запущен")
        print(f"📡 HiveMQ Cloud: {settings.MQTT_HOST}:{settings.MQTT_PORT}")
        print(f"📬 Топик: {settings.MQTT_TOPIC}")
    else:
        print("⚠️ Backend работает без MQTT")

    print("=" * 70 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    print("\n🛑 Остановка сервиса...")
    mqtt_service.disconnect()
    print("✅ Сервис остановлен")


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "parameters": ["temperature", "humidity", "co2_ppm", "co_ppm", "lux"],
        "mqtt": {
            "broker": settings.MQTT_HOST,
            "port": settings.MQTT_PORT,
            "topic": settings.MQTT_TOPIC,
            "connected": mqtt_service.client.is_connected() if mqtt_service.client else False
        },
        "websockets": len(storage.active_websockets),
        "last_update": storage.current_data.get("timestamp"),
        "measurements": len(storage.data_history)
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,     # совет: поставь 0.0.0.0 если нужно с телефона
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info",
        ws_ping_interval=30,
        ws_ping_timeout=60,
    )
