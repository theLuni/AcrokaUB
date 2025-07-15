import asyncio
import re
import random
import string
from pathlib import Path
from typing import Optional, Tuple
import getpass

import aiohttp
from telethon import TelegramClient, errors
from telethon.errors import FloodWaitError, RPCError
from config import API_ID, API_HASH

class BotManager:
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent.resolve()
        self.SOURCE_DIR = self.BASE_DIR / 'source'
        self.SOURCE_DIR.mkdir(exist_ok=True)
        
        self.BOT_TOKEN_FILE = self.SOURCE_DIR / 'bottoken.txt'
        self.BOT_IMAGE = self.SOURCE_DIR / 'pic.png'
        self.DEFAULT_PREFIX = '.'
        
        self.client = TelegramClient(
            session=f'acroka_session_{API_ID}',
            api_id=API_ID,
            api_hash=API_HASH
        )

    async def async_input(self, prompt: str = "") -> str:
        """Асинхронный ввод данных"""
        print(prompt, end="", flush=True)
        return (await asyncio.get_event_loop().run_in_executor(None, lambda: input())).strip()

    async def ensure_connection(self):
        """Проверка и восстановление подключения"""
        if not self.client.is_connected():
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    await self.authenticate()
            except Exception as e:
                raise ConnectionError(f"Ошибка подключения: {e}")

    async def authenticate(self):
        """Процесс авторизации"""
        print("\n🔐 Требуется авторизация в Telegram")
        
        while True:
            try:
                phone = await self.async_input("Введите номер телефона (+7XXX...): ")
                if not phone.startswith('+'):
                    print("❌ Номер должен начинаться с '+'")
                    continue
                
                await self.client.send_code_request(phone)
                break
            except Exception as e:
                print(f"❌ Ошибка запроса кода: {e}")

        while True:
            try:
                code = await self.async_input("Введите код из SMS: ")
                await self.client.sign_in(phone=phone, code=code)
                break
            except errors.SessionPasswordNeededError:
                password = await self.async_input("Введите пароль 2FA: ")
                await self.client.sign_in(password=password)
                break
            except errors.PhoneCodeInvalidError:
                print("❌ Неверный код, попробуйте снова")
            except Exception as e:
                print(f"❌ Ошибка авторизации: {e}")
                return False

        return True

    async def create_new_bot(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Создание нового бота через BotFather"""
        try:
            await self.ensure_connection()
            
            async with self.client.conversation('BotFather') as conv:
                await conv.send_message('/newbot')
                await conv.get_response()
                
                await conv.send_message('Acroka Helper Bot')
                await conv.get_response()

                username = f'acroka_{"".join(random.choices(string.ascii_lowercase + string.digits, k=8))}_bot'
                await conv.send_message(username)
                response = await conv.get_response()

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    self.BOT_TOKEN_FILE.write_text(f"{username}:{user_id}:{token}")
                    print(f"✅ Бот @{username} создан!")
                    return username, user_id, token

        except Exception as e:
            print(f"❌ Ошибка создания бота: {e}")
        return None, None, None

    async def run(self):
        """Основной цикл работы"""
        try:
            await self.ensure_connection()
            me = await self.client.get_me()
            print(f"\n🔑 Авторизован как: {me.first_name}")

            if not self.BOT_TOKEN_FILE.exists():
                print("\n🛠️ Создание нового бота...")
                result = await self.create_new_bot()
                if not result:
                    raise RuntimeError("Не удалось создать бота")
            else:
                content = self.BOT_TOKEN_FILE.read_text().strip()
                if content.count(':') >= 2:
                    username, _, _ = content.split(':', 2)
                    print(f"\n🤖 Используется бот: @{username}")

            # Здесь можно добавить загрузку модулей
            print("\n🚀 Бот готов к работе!")

            # Бесконечный цикл для поддержания соединения
            while True:
                await asyncio.sleep(3600)  # Проверка каждые 60 минут

        except KeyboardInterrupt:
            print("\n🛑 Остановлено пользователем")
        except Exception as e:
            print(f"\n🛑 Критическая ошибка: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()
            print("🔌 Соединение закрыто")

if __name__ == '__main__':
    bot = BotManager()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Программа завершена")
    except Exception as e:
        print(f"🛑 Фатальная ошибка: {e}")
