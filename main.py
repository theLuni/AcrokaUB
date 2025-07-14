import asyncio
import os
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
        # Используем Path для работы с путями
        self.BASE_DIR = Path(__file__).parent.resolve()
        self.SOURCE_DIR = self.BASE_DIR / 'source'
        self.SOURCE_DIR.mkdir(exist_ok=True)
        
        self.BOT_TOKEN_FILE = self.SOURCE_DIR / 'bottoken.txt'
        self.BOT_IMAGE = self.SOURCE_DIR / 'pic.png'
        self.PREFIX_FILE = self.SOURCE_DIR / 'prefix.txt'
        self.DEFAULT_PREFIX = '.'
        
        try:
            self.client = TelegramClient(f'acroka_session_{API_ID}', API_ID, API_HASH)
        except Exception as e:
            raise RuntimeError(f"Ошибка инициализации Telegram клиента: {e}")

    async def async_input(self, prompt: str = "") -> str:
        """Асинхронная замена для input()"""
        print(prompt, end="", flush=True)
        return (await asyncio.get_event_loop().run_in_executor(None, lambda: input())).strip()

    async def sleep(self, delay: float = 1.0) -> None:
        """Асинхронная задержка"""
        await asyncio.sleep(delay)

    def get_prefix(self) -> str:
        """Получение префикса команд"""
        try:
            if self.PREFIX_FILE.exists():
                prefix = self.PREFIX_FILE.read_text().strip()
                return prefix if len(prefix) == 1 else self.DEFAULT_PREFIX
            return self.DEFAULT_PREFIX
        except Exception as e:
            print(f"⚠️ Ошибка чтения файла префикса: {e}")
            return self.DEFAULT_PREFIX

    async def create_new_bot(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Создание нового бота через BotFather"""
        print("🛠️ Создание нового бота...")
        
        async def handle_conversation_step(conv, message: str, expected_response: str = None) -> Optional[str]:
            """Обработка шага диалога"""
            try:
                await conv.send_message(message)
                await self.sleep(2)
                response = await conv.get_response()
                
                if expected_response and expected_response not in response.text:
                    print(f"❌ Неожиданный ответ от BotFather: {response.text}")
                    return None
                return response.text
            except FloodWaitError as e:
                print(f"⏳ Ожидание из-за флуда: {e.seconds} секунд")
                await asyncio.sleep(e.seconds + 5)
                return None
            except RPCError as e:
                print(f"❌ Ошибка RPC: {e}")
                return None
            except Exception as e:
                print(f"❌ Ошибка в диалоге: {e}")
                return None

        try:
            async with self.client.conversation('BotFather', timeout=30) as conv:
                if not await handle_conversation_step(conv, '/newbot', "Alright"):
                    return None, None, None

                if not await handle_conversation_step(conv, 'Acroka Helper Bot'):
                    return None, None, None

                username = self.generate_username()
                response_text = await handle_conversation_step(conv, username, "Done!")
                if not response_text:
                    return None, None, None

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response_text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    try:
                        self.BOT_TOKEN_FILE.write_text(f"{username}:{user_id}:{token}")
                    except Exception as e:
                        print(f"⚠️ Ошибка сохранения токена: {e}")
                        return None, None, None

                    await self.set_bot_photo(username)
                    print(f"✅ Бот @{username} успешно создан!")
                    return username, user_id, token

        except Exception as e:
            print(f"❌ Ошибка при создании бота: {e}")
            return None, None, None

    def generate_username(self) -> str:
        """Генерация имени бота"""
        chars = string.ascii_lowercase + string.digits
        return f'acroka_{"".join(random.choices(chars, k=8))}_bot'

    async def set_bot_photo(self, username: str) -> bool:
        """Установка аватарки"""
        if not self.BOT_IMAGE.exists():
            print(f"⚠️ Файл аватарки {self.BOT_IMAGE} не найден")
            return False

        try:
            async with self.client.conversation('BotFather', timeout=30) as conv:
                steps = [('/setuserpic', None), (f'@{username}', None), (self.BOT_IMAGE, None)]
                
                for message, _ in steps:
                    try:
                        if isinstance(message, str):
                            await conv.send_message(message)
                        else:
                            await conv.send_file(message)
                        await self.sleep(2)
                        await conv.get_response()
                    except Exception as e:
                        print(f"⚠️ Ошибка установки аватарки: {e}")
                        return False

                print("🖼️ Аватарка установлена!")
                return True
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            return False

    async def load_existing_bot(self, username: str) -> Tuple[Optional[str], Optional[str]]:
        """Загрузка существующего бота"""
        print(f"🔍 Загрузка бота @{username}...")
        
        try:
            async with self.client.conversation('BotFather', timeout=30) as conv:
                await conv.send_message('/token')
                await self.sleep(2)
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await self.sleep(2)
                response = await conv.get_response()

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    try:
                        self.BOT_TOKEN_FILE.write_text(f"{username}:{user_id}:{token}")
                    except Exception as e:
                        print(f"⚠️ Ошибка сохранения токена: {e}")
                        return None, None

                    await self.set_bot_photo(username)
                    print(f"✅ Бот @{username} загружен!")
                    return username, token

        except Exception as e:
            print(f"❌ Ошибка при загрузке: {e}")
        return None, None

    async def check_bot_token(self, token: str) -> bool:
        """Проверка токена"""
        url = f'https://api.telegram.org/bot{token}/getMe'
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200 and (await resp.json()).get('ok', False)
        except Exception as e:
            print(f"⚠️ Ошибка проверки токена: {e}")
            return False

    async def run(self) -> None:
        """Основной цикл работы"""
        try:
            # Авторизация
            if not await self.client.is_user_authorized():
                print("\n🔐 Требуется авторизация")
                
                while True:
                    try:
                        phone = await self.async_input("Введите номер телефона (+7XXX...): ")
                        if not phone.startswith('+'):
                            print("❌ Номер должен начинаться с '+'")
                            continue
                            
                        await self.client.send_code_request(phone)
                        break
                    except Exception as e:
                        print(f"❌ Ошибка: {e}")

                while True:
                    try:
                        code = await self.async_input("Введите код из SMS: ")
                        try:
                            await self.client.sign_in(phone=phone, code=code)
                            break
                        except errors.SessionPasswordNeededError:
                            password = await self.async_input("Введите пароль 2FA: ")
                            await self.client.sign_in(password=password)
                            break
                    except errors.PhoneCodeInvalidError:
                        print("❌ Неверный код")
                    except Exception as e:
                        print(f"❌ Ошибка авторизации: {e}")
                        return

            me = await self.client.get_me()
            print(f"\n✅ Авторизован как: {me.first_name}")

            # Работа с ботом
            if not self.BOT_TOKEN_FILE.exists() or not self.BOT_TOKEN_FILE.stat().st_size:
                print("\nℹ️ Файл токена не найден")
                choice = await self.async_input("Создать (1) или загрузить (2) бота? [1/2]: ")
                
                if choice.strip() == '2':
                    username = await self.async_input("Введите @username: ").strip()
                    if not username:
                        print("❌ Имя обязательно")
                        return
                        
                    result = await self.load_existing_bot(username)
                    if not result:
                        return
                    username, token = result
                    print(f"✅ Бот @{username} загружен")
                else:
                    result = await self.create_new_bot()
                    if not result:
                        return
                    username, user_id, token = result
            else:
                try:
                    content = self.BOT_TOKEN_FILE.read_text().strip()
                    if content.count(':') >= 2:
                        username, user_id, token = content.split(':', 2)
                        if not await self.check_bot_token(token):
                            print("❌ Недействительный токен")
                            return
                        print(f"✅ Найден бот @{username}")
                    else:
                        print("❌ Неверный формат токена")
                        return
                except Exception as e:
                    print(f"❌ Ошибка чтения токена: {e}")
                    return

            # Запуск модулей
            try:
                from modules import main as modules_main
                print("\n🚀 Запуск модулей...")
                await modules_main(self.client)
            except ImportError as e:
                print(f"❌ Модули не найдены: {e}")
            except Exception as e:
                print(f"❌ Ошибка модулей: {e}")

        except KeyboardInterrupt:
            print("\n🛑 Остановлено пользователем")
        except Exception as e:
            print(f"\n🛑 Критическая ошибка: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()
                print("🔌 Отключено")


if __name__ == '__main__':
    try:
        bot = BotManager()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Скрипт остановлен")
    except Exception as e:
        print(f"🛑 Фатальная ошибка: {e}")
