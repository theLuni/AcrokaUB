import asyncio
import os
import re
import random
import string
from pathlib import Path
from typing import Optional, Tuple, List
import subprocess 
import aiohttp
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError
from config import API_ID, API_HASH
import platform

class BotManager:
    def __init__(self):
        # 📂 Инициализация путей
        self.BASE_DIR = Path(__file__).parent.resolve()
        self.SOURCE_DIR = self.BASE_DIR / 'source'
        self.SOURCE_DIR.mkdir(exist_ok=True)
        
        # 🔑 Файлы конфигурации
        self.BOT_TOKEN_FILE = self.SOURCE_DIR / 'bottoken.txt'
        self.BOT_IMAGE = self.SOURCE_DIR / 'bot_avatar.png'
        self.PREFIX_FILE = self.SOURCE_DIR / 'prefix.txt'
        self.DEFAULT_PREFIX = '.'
        
        # 🧩 Папка для модулей
        self.MODS_DIR = self.SOURCE_DIR / 'mods'
        self.MODS_DIR.mkdir(exist_ok=True)
        
        # ⚡ Инициализация клиента
        try:
            self.client = TelegramClient(
                session=f'acroka_session_{API_ID}',
                api_id=API_ID,
                api_hash=API_HASH,
                device_model="Bot Manager",
                system_version="1.0",
                app_version="2.0"
            )
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка инициализации клиента: {e}")
            
    async def sleep(self, delay: float = 1.0) -> None:
        """⏳ Асинхронная задержка с обработкой исключений"""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"⚠️ Ошибка при задержке: {e}")

    def get_prefix(self) -> str:
        """🔤 Получение префикса команд"""
        try:
            if self.PREFIX_FILE.exists():
                prefix = self.PREFIX_FILE.read_text().strip()
                return prefix if len(prefix) == 1 else self.DEFAULT_PREFIX
            return self.DEFAULT_PREFIX
        except Exception as e:
            print(f"⚠️ Ошибка чтения префикса: {e}")
            return self.DEFAULT_PREFIX

    async def create_new_bot(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """🤖 Создание нового бота через BotFather"""
        print("\n🛠️ Начинаем процесс создания бота...")
        
        async def botfather_step(conv, message: str, expected: str = None) -> Optional[str]:
            """🔄 Обработка шага диалога с BotFather"""
            try:
                await conv.send_message(message)
                await self.sleep(2.5)  # Оптимальная задержка
                response = await conv.get_response()
                
                if expected and expected.lower() not in response.text.lower():
                    print(f"❌ Неожиданный ответ: {response.text[:50]}...")
                    return None
                return response.text
            except FloodWaitError as e:
                print(f"⏳ Ожидаем {e.seconds} сек. из-за ограничений...")
                await asyncio.sleep(e.seconds + 2)
                return None
            except Exception as e:
                print(f"❌ Ошибка в диалоге: {e}")
                return None

        try:
            async with self.client.conversation('BotFather', timeout=60) as conv:
                # 1. Инициируем создание
                if not await botfather_step(conv, '/newbot', "Alright"):
                    return None, None, None

                # 2. Устанавливаем имя
                if not await botfather_step(conv, 'Acroka Helper Bot'):
                    return None, None, None

                # 3. Генерируем username
                username = self._generate_username()
                response = await botfather_step(conv, username, "Done!")
                if not response:
                    return None, None, None

                # 🔍 Извлекаем токен
                if match := re.search(r'(\d+:[a-zA-Z0-9_-]{35})', response):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    # 💾 Сохраняем данные
                    self._save_bot_data(username, user_id, token)
                    
                    # 🖼️ Устанавливаем аватар
                    await self._set_bot_avatar(username)
                    
                    print(f"\n✅ Бот @{username} успешно создан!")
                    return username, user_id, token

        except Exception as e:
            print(f"❌ Ошибка создания бота: {e}")
        return None, None, None

    def _generate_username(self) -> str:
        """🎲 Генерация уникального username"""
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return f'acroka_{suffix}_bot'

    def _save_bot_data(self, username: str, user_id: str, token: str) -> bool:
        """💾 Сохранение данных бота"""
        try:
            data = f"{username}:{user_id}:{token}"
            self.BOT_TOKEN_FILE.write_text(data)
            return True
        except Exception as e:
            print(f"⚠️ Ошибка сохранения токена: {e}")
            return False

    async def _set_bot_avatar(self, username: str) -> bool:
        """🖼️ Установка аватара бота"""
        if not self.BOT_IMAGE.exists():
            print(f"⚠️ Файл аватара {self.BOT_IMAGE.name} не найден")
            return False

        try:
            async with self.client.conversation('BotFather', timeout=60) as conv:
                steps = [
                    ('/setuserpic', None),
                    (f'@{username}', None),
                    (self.BOT_IMAGE, None)
                ]
                
                for msg, _ in steps:
                    if isinstance(msg, str):
                        await conv.send_message(msg)
                    else:
                        await conv.send_file(msg)
                    await self.sleep(2)
                    await conv.get_response()

                print("🖼️ Аватар успешно установлен!")
                return True
        except Exception as e:
            print(f"⚠️ Ошибка установки аватара: {e}")
            return False

    async def load_existing_bot(self, username: str) -> Tuple[Optional[str], Optional[str]]:
        """🔍 Загрузка существующего бота"""
        print(f"\n🔎 Ищем бота @{username}...")
        
        try:
            async with self.client.conversation('BotFather', timeout=60) as conv:
                await conv.send_message('/token')
                await self.sleep(2)
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await self.sleep(2)
                response = await conv.get_response()

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]{35})', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    
                    if self._save_bot_data(username, user_id, token):
                        await self._set_bot_avatar(username)
                        print(f"\n✅ Бот @{username} загружен!")
                        return username, token

        except Exception as e:
            print(f"❌ Ошибка загрузки бота: {e}")
        return None, None

    async def check_bot_token(self, token: str) -> bool:
        """🔍 Проверка валидности токена"""
        url = f'https://api.telegram.org/bot{token}/getMe'
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    return data.get('ok', False) and resp.status == 200
                    
        except asyncio.TimeoutError:
            print("⚠️ Таймаут проверки токена")
            return False
        except Exception as e:
            print(f"⚠️ Ошибка проверки токена: {e}")
            return False

    async def check_internet_connection(self) -> bool:
        try:
            # Определяем операционную систему
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            # Выполняем команду ping на Google DNS
            output = subprocess.check_output(['ping', param, '1', '8.8.8.8'], stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

async def run(self) -> None:
    """🚀 Основной цикл работы"""
    try:
        # Проверка интернет-соединения
        if not await self.check_internet_connection():
            print("⚠️ [Ошибка] Нет интернет-соединения. Проверьте ваше соединение.")
            return

        # 🔑 Подключение к Telegram
        await self.client.start()
        me = await self.client.get_me()
        print(f"\n👤 Авторизован как: {me.first_name} (ID: {me.id})")

        # 🤖 Инициализация бота
        if not self.BOT_TOKEN_FILE.exists() or not self.BOT_TOKEN_FILE.stat().st_size:
            choice = input("\n📝 Файл токена пуст. Загрузить существующего бота? (да/нет): ").lower()
            
            if choice in ('y', 'yes', 'да', 'д'):
                username = input("Введите @username бота: ").strip()
                if username.startswith('@'):
                    username = username[1:]
                    
                if not username:
                    print("🛑 Не указано имя бота")
                    return
                    
                result = await self.load_existing_bot(username)
                if not result:
                    print("🛑 Не удалось загрузить бота")
                    return
            else:
                result = await self.create_new_bot()
                if not result:
                    print("🛑 Не удалось создать бота")
                    return
        else:
            try:
                content = self.BOT_TOKEN_FILE.read_text().strip()
                if content.count(':') >= 2:
                    parts = content.split(':')
                    token = ':'.join(parts[2:])
                    
                    if not await self.check_bot_token(token):
                        print("❌ Токен недействителен")
                        return
                else:
                    print("❌ Неверный формат токена")
                    return
            except Exception as e:
                print(f"❌ Ошибка чтения токена: {e}")
                return

        # 🧩 Загрузка модулей
        try:
            # Проверяем наличие модулей
            if not any(self.MODS_DIR.iterdir()):
                print("\nℹ️ Папка с модулями пуста. Вы можете добавить модули вручную в source/mods/")
                print("ℹ️ Или используйте команды .dlm или .lm для загрузки модулей")
            else:
                from modules import main as modules_main
                await modules_main(self.client)
                print("\n🔌 Модули успешно загружены")
        except ImportError as e:
            print(f"\n⚠️ Ошибка импорта модулей: {e}")
        except Exception as e:
            print(f"\n❌ Ошибка загрузки модулей: {e}")
            import traceback
            traceback.print_exc()

    except KeyboardInterrupt:
        print("\n🛑 Работа остановлена")
    except Exception as e:
        print(f"\n🛑 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if self.client.is_connected():
            await self.client.disconnect()
            print("\n🔌 Соединение закрыто")
            
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🤖 Acroka Bot Manager".center(50))
    print("="*50 + "\n")
    
    try:
        manager = BotManager()
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        print("\n🛑 Скрипт остановлен")
    except Exception as e:
        print(f"\n💥 Фатальная ошибка: {e}")
    finally:
        print("\n🏁 Работа завершена\n")
