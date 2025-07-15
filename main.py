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
        self.PREFIX_FILE = self.SOURCE_DIR / 'prefix.txt'
        self.DEFAULT_PREFIX = '.'
        
        self.client = TelegramClient(f'acroka_session_{API_ID}', API_ID, API_HASH)
        self.client.parse_mode = 'html'

    async def async_input(self, prompt: str = "") -> str:
        print(prompt, end="", flush=True)
        return (await asyncio.get_event_loop().run_in_executor(None, lambda: input())).strip()

    async def ensure_connection(self):
        """Гарантирует активное подключение"""
        if not self.client.is_connected():
            await self.client.connect()

    async def create_new_bot(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        await self.ensure_connection()
        
        async with self.client.conversation('BotFather', timeout=30) as conv:
            try:
                await conv.send_message('/newbot')
                await asyncio.sleep(2)
                response = await conv.get_response()
                
                if "Alright" not in response.text:
                    return None, None, None

                await conv.send_message('Acroka Helper Bot')
                await asyncio.sleep(2)
                await conv.get_response()

                username = f'acroka_{"".join(random.choices(string.ascii_lowercase + string.digits, k=8))}_bot'
                await conv.send_message(username)
                await asyncio.sleep(2)
                response = await conv.get_response()

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    self.BOT_TOKEN_FILE.write_text(f"{username}:{user_id}:{token}")
                    await self.set_bot_photo(username)
                    return username, user_id, token

            except Exception as e:
                print(f"❌ Ошибка создания бота: {e}")
                return None, None, None

    async def run(self) -> None:
        try:
            # Подключение и авторизация
            await self.ensure_connection()
            
            if not await self.client.is_user_authorized():
                print("\n🔐 Требуется авторизация")
                phone = await self.async_input("Введите номер телефона (+7XXX...): ")
                
                while not phone.startswith('+'):
                    print("❌ Номер должен начинаться с '+'")
                    phone = await self.async_input("Введите номер телефона (+7XXX...): ")
                
                try:
                    await self.client.send_code_request(phone)
                    code = await self.async_input("Введите код из SMS: ")
                    
                    try:
                        await self.client.sign_in(phone=phone, code=code)
                    except errors.SessionPasswordNeededError:
                        password = await self.async_input("Введите пароль 2FA: ")
                        await self.client.sign_in(password=password)
                
                except Exception as e:
                    print(f"❌ Ошибка авторизации: {e}")
                    return

            me = await self.client.get_me()
            print(f"\n✅ Авторизован как: {me.first_name}")

            # Основная логика работы с ботом
            if not self.BOT_TOKEN_FILE.exists():
                choice = await self.async_input("Создать нового бота? (да/нет): ")
                if choice.lower() in ('да', 'д', 'yes', 'y'):
                    result = await self.create_new_bot()
                    if not result:
                        print("❌ Не удалось создать бота")
                        return
                    print(f"✅ Бот @{result[0]} создан!")
                else:
                    print("❌ Требуется токен бота")
                    return
            else:
                content = self.BOT_TOKEN_FILE.read_text().strip()
                if content.count(':') >= 2:
                    username, user_id, token = content.split(':', 2)
                    print(f"✅ Используется бот @{username}")

            # Запуск дополнительных модулей
            try:
                from modules import main as modules_main
                print("\n🚀 Запуск модулей...")
                await modules_main(self.client)
            except ImportError:
                print("ℹ️ Дополнительные модули не найдены")

        except KeyboardInterrupt:
            print("\n🛑 Остановлено пользователем")
        except Exception as e:
            print(f"\n🛑 Ошибка: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()
                print("🔌 Отключено от Telegram")


if __name__ == '__main__':
    try:
        bot = BotManager()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Скрипт остановлен")
    except Exception as e:
        print(f"🛑 Фатальная ошибка: {e}")
