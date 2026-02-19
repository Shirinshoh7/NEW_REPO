"""
MQTT сервис для получения данных от ESP32
"""
import paho.mqtt.client as mqtt
import json
import ssl
import asyncio
import time
from typing import Optional
from ..config import settings
from ..core.storage import storage


class MQTTService:
    """Сервис MQTT"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._danger_state_by_device: dict[str, bool] = {}
        self._last_alert_ts_by_device: dict[str, float] = {}
    
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

    def _build_alert_message(self, data: dict, profile: dict, issues: list[str]) -> str:
        """Формирует понятный текст уведомления по профилю и отклонениям."""
        profile_name = profile.get("name", "Профиль")
        parts: list[str] = []

        temp = float(data.get("temperature", 0))
        hum = float(data.get("humidity", 0))
        co2 = float(data.get("co2_ppm", 0))
        co = float(data.get("co_ppm", data.get("co", 0)))
        lux = float(data.get("lux", 0))

        if "temperature" in issues:
            tmin = profile.get("temp_min")
            tmax = profile.get("temp_max")
            parts.append(f"температура {temp:.1f}°C (норма {tmin}-{tmax}°C)")
        if "humidity" in issues:
            hmax = profile.get("humidity_max")
            parts.append(f"влажность {hum:.0f}% (макс {hmax}%)")
        if "co2_ppm" in issues:
            cmax = profile.get("co2_max")
            parts.append(f"CO2 {co2:.0f} ppm (макс {cmax})")
        if "co_ppm" in issues:
            comax = profile.get("co_max")
            parts.append(f"CO {co:.1f} ppm (макс {comax})")
        if "lux" in issues:
            lmin = profile.get("lux_min")
            lmax = profile.get("lux_max")
            parts.append(f"освещенность {lux:.0f} lx (норма {lmin}-{lmax})")

        if not parts:
            parts.append("есть отклонение параметров")

        return f"{profile_name}: {', '.join(parts)}. Проверьте помещение."
    
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
                "co_ppm": float(payload.get("co_ppm", payload.get("co", 0))),
                "lux": float(illuminance),
                "device_id": payload.get("device_id", "esp32_main")
            }
            
            # Обновление хранилища
            storage.update_current_data(data)
            
            print(f"📊 T={data['temperature']:.1f}°C, "
                  f"H={data['humidity']:.0f}%, "
                  f"CO2={data['co2_ppm']:.0f}ppm, "
                  f"CO={data['co_ppm']:.1f}ppm, "
                  f"LUX={data['lux']:.0f}lx")

            # Push в FCM отправляем только при переходе в аварийное состояние.
            latest = storage.data_history[-1] if storage.data_history else {}
            is_danger = bool(latest.get("is_danger", False))
            device_id = data["device_id"]
            prev_state = self._danger_state_by_device.get(device_id, False)

            # Отправляем push сразу при входе в danger и далее с интервалом reminder.
            now_ts = time.time()
            cooldown = max(0, int(settings.FCM_DANGER_REMINDER_SEC))
            last_alert_ts = self._last_alert_ts_by_device.get(device_id, 0.0)
            should_alert = is_danger and (
                (not prev_state) or (cooldown == 0) or ((now_ts - last_alert_ts) >= cooldown)
            )

            if should_alert:
                from ..services.firebase_service import firebase_service

                issues = latest.get("issues", [])
                profile = storage.active_profile or {}
                issues_text = ", ".join(issues) if issues else "параметры"
                message_body = self._build_alert_message(data, profile, issues)
                target_user_id = settings.FCM_DEFAULT_USER_ID
                delivered = 1 if firebase_service.send_push_to_user(
                    user_id=target_user_id,
                    title="Микроклимат: вне нормы",
                    body=message_body,
                    data={
                        "type": "danger",
                        "device_id": device_id,
                        "profile_name": str(profile.get("name", "")),
                        "issues": issues_text,
                        "temperature": f"{data['temperature']:.1f}",
                        "humidity": f"{data['humidity']:.0f}",
                        "co2_ppm": f"{data['co2_ppm']:.0f}",
                        "co_ppm": f"{data['co_ppm']:.1f}",
                        "lux": f"{data['lux']:.0f}",
                    },
                ) else 0
                self._last_alert_ts_by_device[device_id] = now_ts
                print(
                    f"🔔 FCM alert: device={device_id}, user_id={target_user_id}, "
                    f"delivered_users={delivered}, issues={issues_text}"
                )

            self._danger_state_by_device[device_id] = is_danger
            
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
