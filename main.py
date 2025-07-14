import asyncio
import os
import re
import random
import string
from pathlib import Path
from typing import Optional, Tuple

import aiohttp
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError
from config import API_ID, API_HASH


class BotManager:
    def __init__(self):
        # Используем Path для более надежной работы с путями
        self.BASE_DIR = Path(__file__).parent.resolve()
        self.SOURCE_DIR = self.BASE_DIR / 'source'
        self.SOURCE_DIR.mkdir(exist_ok=True)  # Создаем папку, если ее нет
        
        self.BOT_TOKEN_FILE = self.SOURCE_DIR / 'bottoken.txt'
        self.BOT_IMAGE = self.SOURCE_DIR / 'pic.png'
        self.PREFIX_FILE = self.SOURCE_DIR / 'prefix.txt'
        self.DEFAULT_PREFIX = '.'
        
        # Инициализация клиента с обработкой ошибок
        try:
            self.client = TelegramClient(f'acroka_session_{API_ID}', API_ID, API_HASH)
        except Exception as e:
            raise RuntimeError(f"Ошибка инициализации Telegram клиента: {e}")

    async def async_input(self, prompt: str = "") -> str:
        """Асинхронная замена для input()"""
        print(prompt, end="", flush=True)
        return (await asyncio.get_event_loop().run_in_executor(None, lambda: input())).strip()

    async def sleep(self, delay: float = 1.0) -> None:
        """Асинхронная задержка с обработкой FloodWait"""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"⚠️ Неожиданная ошибка при задержке: {e}")

    def get_prefix(self) -> str:
        """Получение префикса команд из файла"""
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
            """Обработка шага диалога с BotFather"""
            try:
                await conv.send_message(message)
                await self.sleep(2)  # Увеличили задержку для надежности
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
                # Шаг 1: Инициируем создание бота
                if not await handle_conversation_step(conv, '/newbot', "Alright"):
                    return None, None, None

                # Шаг 2: Устанавливаем имя бота
                if not await handle_conversation_step(conv, 'Acroka Helper Bot'):
                    return None, None, None

                # Шаг 3: Устанавливаем username бота
                username = self.generate_username()
                response_text = await handle_conversation_step(conv, username, "Done!")
                if not response_text:
                    return None, None, None

                # Извлекаем токен из ответа
                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response_text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    # Сохраняем токен
                    try:
                        self.BOT_TOKEN_FILE.write_text(f"{username}:{user_id}:{token}")
                    except Exception as e:
                        print(f"⚠️ Ошибка сохранения токена: {e}")
                        return None, None, None

                    # Устанавливаем аватарку
                    await self.set_bot_photo(username)
                    print(f"✅ Бот @{username} успешно создан!")
                    return username, user_id, token

        except Exception as e:
            print(f"❌ Ошибка при создании бота: {e}")
            return None, None, None

    def generate_username(self) -> str:
        """Генерация уникального имени бота"""
        chars = string.ascii_lowercase + string.digits
        rand_part = ''.join(random.choices(chars, k=8))  # Увеличили длину для уникальности
        return f'acroka_{rand_part}_bot'

    async def set_bot_photo(self, username: str) -> bool:
        """Установка аватарки для бота"""
        if not self.BOT_IMAGE.exists():
            print(f"⚠️ Файл аватарки {self.BOT_IMAGE} не найден")
            return False

        try:
            async with self.client.conversation('BotFather', timeout=30) as conv:
                steps = [
                    ('/setuserpic', None),
                    (f'@{username}', None),
                    (self.BOT_IMAGE, None)
                ]
                
                for message, expected in steps:
                    try:
                        if isinstance(message, str):
                            await conv.send_message(message)
                        else:
                            await conv.send_file(message)
                        await self.sleep(2)
                        await conv.get_response()
                    except Exception as e:
                        print(f"⚠️ Ошибка установки аватарки на шаге {message}: {e}")
                        return False

                print("🖼️ Аватарка бота успешно установлена!")
                return True
        except Exception as e:
            print(f"⚠️ Не удалось установить аватарку: {e}")
            return False

    async def load_existing_bot(self, username: str) -> Tuple[Optional[str], Optional[str]]:
        """Загрузка существующего бота"""
        print(f"🔍 Загрузка бота @{username}...")
        
        try:
            async with self.client.conversation('BotFather', timeout=30) as conv:
                # Запрашиваем токен
                await conv.send_message('/token')
                await self.sleep(2)
                await conv.get_response()
                
                # Указываем username бота
                await conv.send_message(f'@{username}')
                await self.sleep(2)
                response = await conv.get_response()

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    # Сохраняем токен
                    try:
                        self.BOT_TOKEN_FILE.write_text(f"{username}:{user_id}:{token}")
                    except Exception as e:
                        print(f"⚠️ Ошибка сохранения токена: {e}")
                        return None, None

                    # Устанавливаем аватарку
                    await self.set_bot_photo(username)
                    print(f"✅ Бот @{username} успешно загружен!")
                    return username, token

        except Exception as e:
            print(f"❌ Ошибка при загрузке бота: {e}")
        return None, None

    async def check_bot_token(self, token: str) -> bool:
        """Проверка валидности токена бота"""
        url = f'https://api.telegram.org/bot{token}/getMe'
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return False
                    
                    data = await resp.json()
                    return data.get('ok', False)
                    
        except asyncio.TimeoutError:
            print("⚠️ Таймаут при проверке токена бота")
            return False
        except Exception as e:
            print(f"⚠️ Ошибка проверки токена бота: {e}")
            return False

    async def run(self) -> None:
    """Основной цикл работы бота"""
    try:
        # Подключаемся к Telegram с обработкой авторизации
        if not await self.client.is_user_authorized():
            print("\n🔐 Требуется авторизация в Telegram")
            
            while True:
                try:
                    phone = await self.async_input("Введите номер телефона (в формате +7XXXXXXXXXX): ")
                    if not phone.startswith('+'):
                        print("❌ Номер должен начинаться с '+' (например, +79123456789)")
                        continue
                        
                    await self.client.send_code_request(phone)
                    break
                except Exception as e:
                    print(f"❌ Ошибка при запросе кода: {e}")

            while True:
                try:
                    code = await self.async_input("Введите код из SMS или Telegram: ")
                    try:
                        await self.client.sign_in(phone=phone, code=code)
                        break
                    except errors.SessionPasswordNeededError:
                        password = await self.async_input("Введите пароль двухфакторной аутентификации: ")
                        await self.client.sign_in(password=password)
                        break
                except errors.PhoneCodeInvalidError:
                    print("❌ Неверный код, попробуйте снова")
                except Exception as e:
                    print(f"❌ Ошибка авторизации: {e}")
                    return

        me = await self.client.get_me()
        print(f"\n✅ Авторизован как: {me.first_name} (id: {me.id})")

        # Проверяем и загружаем токен бота
        if not self.BOT_TOKEN_FILE.exists() or self.BOT_TOKEN_FILE.stat().st_size == 0:
            print("\nℹ️ Файл токена бота не найден или пуст")
            choice = await self.async_input("Создать нового бота (1) или загрузить существующего (2)? [1/2]: ")
            
            if choice.strip() == '2':
                username = await self.async_input("Введите @username бота (без @): ").strip()
                if not username:
                    print("❌ Имя бота не может быть пустым")
                    return
                    
                result = await self.load_existing_bot(username)
                if not result:
                    print("❌ Не удалось загрузить бота")
                    return
                username, token = result
                print(f"✅ Бот @{username} успешно загружен!")
            else:
                result = await self.create_new_bot()
                if not result:
                    print("❌ Не удалось создать бота")
                    return
                username, user_id, token = result
        else:
            try:
                content = self.BOT_TOKEN_FILE.read_text().strip()
                if content.count(':') >= 2:
                    parts = content.split(':')
                    username = parts[0]
                    user_id = parts[1]
                    token = ':'.join(parts[2:])
                    
                    if not await self.check_bot_token(token):
                        print("❌ Токен бота недействителен")
                        return
                        
                    print(f"✅ Найден бот @{username} (ID: {user_id})")
                else:
                    print("❌ Неверный формат файла токена")
                    return
            except Exception as e:
                print(f"❌ Ошибка чтения файла токена: {e}")
                return

        # Запуск модулей
        try:
            from modules import main as modules_main
            print("\n🚀 Запуск модулей бота...")
            await modules_main(self.client)
        except ImportError as e:
            print(f"❌ Ошибка импорта модулей: {e}")
        except Exception as e:
            print(f"❌ Ошибка в модулях: {e}")

    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n🛑 Критическая ошибка: {str(e)}")
    finally:
        if self.client.is_connected():
            await self.client.disconnect()
            print("🔌 Отключено от Telegram")

if __name__ == '__main__':
    try:
        bot = BotManager()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Скрипт остановлен пользователем")
    except Exception as e:
        print(f"🛑 Фатальная ошибка: {str(e)}")
