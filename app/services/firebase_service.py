"""
FCM сервис: регистрация device token и отправка push-уведомлений.
"""
from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Dict, List, Set

import firebase_admin
from firebase_admin import credentials, messaging

from ..config import settings


class FirebaseService:
    """Сервис для работы с Firebase Cloud Messaging."""

    def __init__(self):
        self._lock = Lock()
        self._user_tokens: Dict[str, Set[str]] = defaultdict(set)
        self._initialized = False

    def init_firebase(self) -> bool:
        """Инициализирует Firebase Admin SDK (один раз)."""
        if not settings.FCM_ENABLED:
            print("ℹ️ FCM отключен (FCM_ENABLED=False)")
            return False

        credentials_path = settings.FIREBASE_CREDENTIALS_PATH
        if not credentials_path:
            print("⚠️ FCM включен, но FIREBASE_CREDENTIALS_PATH не задан")
            return False

        try:
            firebase_admin.get_app()
            self._initialized = True
            print("✅ Firebase уже инициализирован")
            return True
        except ValueError:
            pass

        cred_file = Path(credentials_path)
        if not cred_file.exists():
            print(f"⚠️ Файл Firebase credentials не найден: {cred_file}")
            return False

        try:
            cred = credentials.Certificate(str(cred_file))
            firebase_admin.initialize_app(cred)
            self._initialized = True
            print("✅ Firebase инициализирован")
            return True
        except Exception as e:
            print(f"❌ Ошибка инициализации Firebase: {e}")
            return False

    def register_token(self, user_id: str, token: str) -> int:
        """Регистрирует FCM токен и возвращает текущее количество токенов пользователя."""
        with self._lock:
            self._user_tokens[user_id].add(token)
            return len(self._user_tokens[user_id])

    def unregister_token(self, user_id: str, token: str) -> int:
        """Удаляет FCM токен пользователя и возвращает оставшееся количество."""
        with self._lock:
            tokens = self._user_tokens.get(user_id)
            if not tokens:
                return 0
            tokens.discard(token)
            if not tokens:
                self._user_tokens.pop(user_id, None)
                return 0
            return len(tokens)

    def get_tokens_count(self, user_id: str) -> int:
        with self._lock:
            return len(self._user_tokens.get(user_id, set()))

    def get_users_count(self) -> int:
        with self._lock:
            return len(self._user_tokens)

    def _remove_invalid_tokens(self, user_id: str, invalid_tokens: List[str]) -> None:
        if not invalid_tokens:
            return
        with self._lock:
            tokens = self._user_tokens.get(user_id)
            if not tokens:
                return
            for token in invalid_tokens:
                tokens.discard(token)
            if not tokens:
                self._user_tokens.pop(user_id, None)

    def send_push_to_user(self, user_id: str, title: str, body: str, data: Dict[str, str] | None = None) -> bool:
        """Отправляет push указанному пользователю."""
        if not self._initialized:
            if not self.init_firebase():
                print(f"⚠️ FCM не отправлен: Firebase не инициализирован (user_id={user_id})")
                return False

        with self._lock:
            tokens = list(self._user_tokens.get(user_id, set()))

        if not tokens:
            print(f"⚠️ FCM не отправлен: нет токенов для user_id={user_id}")
            return False

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="critical_alerts",
                    sound="default",
                    click_action="FLUTTER_NOTIFICATION_CLICK",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default")
                )
            ),
        )

        try:
            response = messaging.send_each_for_multicast(message)
            invalid_tokens: List[str] = []
            for idx, resp in enumerate(response.responses):
                if resp.success:
                    continue
                code = getattr(resp.exception, "code", "") if resp.exception else ""
                detail = str(resp.exception) if resp.exception else "unknown error"
                print(f"⚠️ FCM token send failed: user_id={user_id}, idx={idx}, code={code}, detail={detail}")
                # Удаляем токен только при явном признаке, что он более не существует.
                if code == "registration-token-not-registered":
                    invalid_tokens.append(tokens[idx])
            self._remove_invalid_tokens(user_id, invalid_tokens)
            print(
                f"📨 FCM send result: user_id={user_id}, success={response.success_count}, "
                f"failed={response.failure_count}, tokens={len(tokens)}"
            )
            return response.success_count > 0
        except Exception as e:
            print(f"❌ Ошибка отправки push для {user_id}: {e}")
            return False

    def send_push_to_all_users(self, title: str, body: str, data: Dict[str, str] | None = None) -> int:
        """Отправляет push всем зарегистрированным пользователям."""
        with self._lock:
            user_ids = list(self._user_tokens.keys())

        success_users = 0
        for user_id in user_ids:
            if self.send_push_to_user(user_id, title, body, data):
                success_users += 1
        return success_users


firebase_service = FirebaseService()
