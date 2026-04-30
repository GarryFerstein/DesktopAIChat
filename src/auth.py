# Импорт необходимых библиотек
import sqlite3
import hashlib
import secrets
from typing import Optional, Tuple
import os
from pathlib import Path
import aiohttp
import asyncio

# Загружаем переменные окружения


def load_env_file():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        return True
    return False


load_env_file()


class AuthManager:
    def __init__(self, db_path: str = "auth.db"):
        self.db_path = Path(__file__).parent.parent / db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth (
                id INTEGER PRIMARY KEY,
                api_key TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def hash_pin(self, pin: str) -> str:
        return hashlib.sha256(pin.encode()).hexdigest()

    def generate_pin(self) -> str:
        return f"{secrets.randbelow(10000):04d}"

    def get_api_key_from_env(self) -> Optional[str]:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('OPENROUTER_API_KEY'):
                            api_key = line.split('=', 1)[1].strip()
                            api_key = api_key.strip('"').strip("'")
                            break
        return api_key if api_key else None

    async def verify_openrouter_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Реальная проверка ключа и баланса через API OpenRouter
        """
        if not api_key or len(api_key) < 20:
            return False, "❌ API ключ слишком короткий или не указан"

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                # Проверяем ключ через API
                async with session.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        credits = data.get('credits', 0)
                        is_free_tier = data.get('is_free_tier', False)

                        if credits > 0:
                            return True, f"✅ Ключ валидный. Баланс: ${credits:.2f}"
                        elif is_free_tier:
                            return True, "✅ Ключ валидный. Используются бесплатные модели (Free Tier).\nБаланс: $0, доступны только бесплатные модели."
                        else:
                            return True, "✅ Ключ валидный.\n⚠️ Баланс нулевой, но доступны бесплатные модели."

                    elif response.status == 401:
                        return False, "❌ Неверный ключ API. Пожалуйста, проверьте ключ и попробуйте снова."
                    else:
                        return False, f"❌ Ошибка проверки ключа: {response.status}"

        except aiohttp.ClientConnectorError:
            return False, "⚠️ Нет подключения к интернету. Проверьте соединение."
        except asyncio.TimeoutError:
            return False, "⏰ Таймаут подключения. Попробуйте позже."
        except Exception as e:
            return False, f"⚠️ Ошибка подключения: {str(e)}"

    def save_credentials(self, api_key: str, pin: str):
        """Сохранение ключа и PIN в базу данных"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM auth")
        pin_hash = self.hash_pin(pin)
        cursor.execute(
            "INSERT INTO auth (api_key, pin_hash) VALUES (?, ?)",
            (api_key, pin_hash)
        )
        conn.commit()
        conn.close()

    def verify_pin(self, pin: str) -> bool:
        """Проверка PIN-кода"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT pin_hash FROM auth LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        if result:
            stored_hash = result[0]
            return self.hash_pin(pin) == stored_hash
        return False

    def get_api_key(self) -> Optional[str]:
        """Получение сохраненного API ключа"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT api_key FROM auth LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def has_credentials(self) -> bool:
        """Проверка наличия сохраненных учетных данных"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM auth")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def reset_credentials(self):
        """Сброс учетных данных"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM auth")
        conn.commit()
        conn.close()
