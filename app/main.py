"""
Главный файл FastAPI приложения
"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import settings
from .services.mqtt_service import mqtt_service
from .core.storage import storage

# Импорт роутеров
from .api.routes import climate, profiles, history, test


# Создание FastAPI приложения
app = FastAPI(
    title=settings.APP_NAME,
    description="Real-Time IoT Backend с MQTT и WebSocket (4 параметра)",
    version=settings.APP_VERSION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(climate.router)
app.include_router(profiles.router)
app.include_router(history.router)
app.include_router(test.router)


@app.on_event("startup")
async def startup_event():
    """Запуск при старте сервера"""
    print("\n" + "=" * 70)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 70)
    print("📊 Поддерживаемые параметры:")
    print("   • Температура (°C)")
    print("   • Влажность (%)")
    print("   • CO2 (ppm)")
    print("   • Освещенность (lux)")
    print("=" * 70)
    
    # Настройка и запуск MQTT
    event_loop = asyncio.get_event_loop()
    mqtt_service.setup(event_loop)
    
    if mqtt_service.connect():
        print(f"✅ MQTT клиент запущен")
        print(f"📡 HiveMQ Cloud: {settings.MQTT_HOST}:{settings.MQTT_PORT}")
        print(f"📬 Топик: {settings.MQTT_TOPIC}")
    else:
        print("⚠️ Backend работает без MQTT")
    
    print("=" * 70 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Остановка при выключении"""
    print("\n🛑 Остановка сервиса...")
    mqtt_service.disconnect()
    print("✅ Сервис остановлен")


@app.get("/")
async def root():
    """Информация о сервере"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "parameters": ["temperature", "humidity", "co2_ppm", "lux"],
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
    print("\n" + "=" * 70)
    print(f"🚀 {settings.APP_NAME}")
    print("=" * 70)
    print("📊 Поддерживает 4 параметра:")
    print("   • 🌡️  Температура")
    print("   • 💧 Влажность")
    print("   • 💨 CO2")
    print("   • ☀️  Освещенность (Lux)")
    print("=" * 70)
    print(f"\n🌐 HTTP API: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"🔌 WebSocket: ws://{settings.SERVER_HOST}:{settings.SERVER_PORT}/api/ws/realtime")
    print(f"📚 Docs: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/docs")
    print(f"\n💡 Тест: POST http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/api/test/inject")
    print("\n⚠️  Нажмите CTRL+C для остановки\n")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
