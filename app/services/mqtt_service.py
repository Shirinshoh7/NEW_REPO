"""
MQTT сервис для получения данных от ESP32
"""
import paho.mqtt.client as mqtt
import json
import ssl
import asyncio
from typing import Optional
from ..config import settings
from ..core.storage import storage


class MQTTService:
    """Сервис MQTT"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
    
    def setup(self, event_loop: asyncio.AbstractEventLoop):
        """Настройка MQTT клиента"""
        self.event_loop = event_loop
        
        self.client = mqtt.Client(
            client_id="backend_microclimate_prod_v2",
            protocol=mqtt.MQTTv311
        )
        
        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Авторизация
        self.client.username_pw_set(
            settings.MQTT_USER,
            settings.MQTT_PASSWORD
        )
        
        # TLS/SSL
        self.client.tls_set(cert_reqs=ssl.CERT_NONE)
        self.client.tls_insecure_set(True)
    
    def connect(self):
        """Подключение к MQTT брокеру"""
        try:
            self.client.connect(
                settings.MQTT_HOST,
                settings.MQTT_PORT,
                60
            )
            self.client.loop_start()
            print(f"✅ MQTT подключен к {settings.MQTT_HOST}:{settings.MQTT_PORT}")
            return True
        except Exception as e:
            print(f"❌ Ошибка MQTT: {e}")
            return False
    
    def disconnect(self):
        """Отключение от MQTT"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            print("✅ MQTT отключен")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback при подключении"""
        if rc == 0:
            print("✅ MQTT подключен к HiveMQ Cloud!")
            client.subscribe(settings.MQTT_TOPIC)
            print(f"📡 Подписка на топик: {settings.MQTT_TOPIC}")
        else:
            error_msgs = {
                1: "Неверная версия протокола",
                2: "Неверный client ID",
                3: "Сервер недоступен",
                4: "Неверный логин/пароль",
                5: "Не авторизован"
            }
            print(f"❌ MQTT ошибка: {error_msgs.get(rc, f'Код {rc}')}")
    
    def _on_message(self, client, userdata, msg):
        """Callback при получении сообщения"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # Обработка разных ключей для освещенности
            illuminance = payload.get("illuminance", 0.0)
            if illuminance == 0:
                illuminance = payload.get("lux", 0.0)
            
            # Подготовка данных
            data = {
                "temperature": float(payload.get("temperature", 0)),
                "humidity": float(payload.get("humidity", 0)),
                "co2_ppm": float(payload.get("co2_ppm", 0)),
                "lux": float(illuminance),
                "device_id": payload.get("device_id", "esp32_main")
            }
            
            # Обновление хранилища
            storage.update_current_data(data)
            
            print(f"📊 T={data['temperature']:.1f}°C, "
                  f"H={data['humidity']:.0f}%, "
                  f"CO2={data['co2_ppm']:.0f}ppm, "
                  f"LUX={data['lux']:.0f}lx")
            
            # Broadcast через WebSocket
            if self.event_loop:
                from ..services.websocket_service import websocket_service
                asyncio.run_coroutine_threadsafe(
                    websocket_service.broadcast(storage.current_data),
                    self.event_loop
                )
        
        except Exception as e:
            print(f"❌ Ошибка обработки MQTT: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback при отключении"""
        if rc != 0:
            print(f"⚠️ MQTT отключен. Переподключение...")


# Глобальный экземпляр сервиса
mqtt_service = MQTTService()
