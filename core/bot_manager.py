import asyncio
import os
import re
import random
import string
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple
import aiohttp
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from config import API_ID, API_HASH

class BotManager:
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent.parent.resolve()
        self.SOURCE_DIR = self.BASE_DIR / 'source'
        self.SOURCE_DIR.mkdir(exist_ok=True)
        
        self.BOT_TOKEN_FILE = self.SOURCE_DIR / 'bottoken.txt'
        self.BOT_IMAGE = self.SOURCE_DIR / 'bot_avatar.png'
        self.PREFIX_FILE = self.SOURCE_DIR / 'prefix.txt'
        self.DEFAULT_PREFIX = '.'
        
        self.MODS_DIR = self.SOURCE_DIR / 'mods'
        self.MODS_DIR.mkdir(exist_ok=True)
        
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Инициализация клиента Telegram"""
        try:
            self.client = TelegramClient(
                session=f'acroka_session_{API_ID}',
                api_id=API_ID,
                api_hash=API_HASH,
                device_model="Acroka UserBot",
                system_version="3.0",
                app_version="3.0",
                lang_code="ru",
                system_lang_code="ru-RU"
            )
        except Exception as e:
            raise RuntimeError(f"❌ Ошибка инициализации клиента: {e}")
    
    async def sleep(self, delay: float = 1.0) -> None:
        """Асинхронная задержка"""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
    
    def get_prefix(self) -> str:
        """Получение префикса команд"""
        try:
            if self.PREFIX_FILE.exists():
                prefix = self.PREFIX_FILE.read_text().strip()
                return prefix if 0 < len(prefix) <= 3 else self.DEFAULT_PREFIX
            return self.DEFAULT_PREFIX
        except Exception:
            return self.DEFAULT_PREFIX
    
    async def create_new_bot(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Создание нового бота через BotFather"""
        print("\n" + "🛠️ Создание нового бота".center(50, '─'))
        
        async def botfather_step(conv, message: str, delay: float = 2.5) -> Optional[str]:
            """Обработка шага диалога с BotFather"""
            try:
                await conv.send_message(message)
                await self.sleep(delay)
                response = await conv.get_response()
                return response.text
            except FloodWaitError as e:
                print(f"⏳ Ожидаем {e.seconds} сек. из-за ограничений...")
                await asyncio.sleep(e.seconds + 2)
                return None
            except Exception as e:
                print(f"⚠️ Ошибка в диалоге: {e}")
                return None
        
        try:
            async with self.client.conversation('BotFather', timeout=60) as conv:
                # 1. Начало создания
                if not await botfather_step(conv, '/newbot'):
                    return None, None, None
                
                # 2. Устанавливаем имя бота
                if not await botfather_step(conv, 'Acroka Helper Bot v3'):
                    return None, None, None
                
                # 3. Генерируем username
                username = self._generate_username()
                response = await botfather_step(conv, username, 3.0)
                
                if not response:
                    return None, None, None
                
                # Извлекаем токен
                token_match = re.search(r'(\d+:[a-zA-Z0-9_-]{35})', response)
                if token_match:
                    token = token_match.group(1)
                    user_id = token.split(':')[0]
                    
                    # Сохраняем данные
                    if self._save_bot_data(username, user_id, token):
                        # Пытаемся установить аватар
                        await self._set_bot_avatar(username)
                        
                        print(f"\n" + "✅ БОТ СОЗДАН".center(50, '─'))
                        print(f"👤 Username: @{username}")
                        print(f"🆔 Bot ID: {user_id}")
                        print(f"🔐 Token: {token[:15]}...")
                        print("─" * 50)
                        
                        return username, user_id, token
        
        except Exception as e:
            print(f"❌ Ошибка создания бота: {e}")
        
        return None, None, None
    
    def _generate_username(self) -> str:
        """Генерация уникального username"""
        adjectives = ['smart', 'quick', 'fast', 'cool', 'super', 'mega', 'ultra']
        nouns = ['helper', 'assistant', 'bot', 'agent', 'manager']
        
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        return f'{adj}_{noun}_{suffix}_bot'
    
    def _save_bot_data(self, username: str, user_id: str, token: str) -> bool:
        """Сохранение данных бота"""
        try:
            data = f"{username}:{user_id}:{token}"
            self.BOT_TOKEN_FILE.write_text(data)
            
            # Дублируем в удобном формате
            info_file = self.SOURCE_DIR / 'bot_info.txt'
            info_file.write_text(
                f"🤖 Acroka Bot Information\n"
                f"─────────────────────────\n"
                f"Username: @{username}\n"
                f"Bot ID: {user_id}\n"
                f"Token: {token}\n"
                f"─────────────────────────\n"
                f"Created: {self._get_current_time()}\n"
            )
            
            return True
        except Exception as e:
            print(f"⚠️ Ошибка сохранения данных бота: {e}")
            return False
    
    def _get_current_time(self) -> str:
        """Получение текущего времени"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    async def _set_bot_avatar(self, username: str) -> bool:
        """Установка аватара бота"""
        if not self.BOT_IMAGE.exists():
            print(f"ℹ️ Файл аватара не найден, пропускаем установку")
            return False
        
        try:
            async with self.client.conversation('BotFather', timeout=60) as conv:
                await conv.send_message('/setuserpic')
                await self.sleep(2)
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await self.sleep(2)
                await conv.get_response()
                
                await conv.send_file(self.BOT_IMAGE)
                await self.sleep(2)
                response = await conv.get_response()
                
                if 'Great' in response.text or 'Хорошо' in response.text:
                    print("🖼️ Аватар успешно установлен!")
                    return True
                else:
                    print("⚠️ Не удалось установить аватар")
                    return False
        except Exception as e:
            print(f"⚠️ Ошибка установки аватара: {e}")
            return False
    
    async def load_existing_bot(self, username: str) -> Tuple[Optional[str], Optional[str]]:
        """Загрузка существующего бота"""
        print(f"\n🔍 Поиск бота @{username}...")
        
        try:
            async with self.client.conversation('BotFather', timeout=60) as conv:
                await conv.send_message('/token')
                await self.sleep(2)
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await self.sleep(2)
                response = await conv.get_response()
                
                token_match = re.search(r'(\d+:[a-zA-Z0-9_-]{35})', response.text)
                if token_match:
                    token = token_match.group(1)
                    user_id = token.split(':')[0]
                    
                    if self._save_bot_data(username, user_id, token):
                        await self._set_bot_avatar(username)
                        print(f"\n✅ Бот @{username} загружен!")
                        return username, token
        
        except Exception as e:
            print(f"❌ Ошибка загрузки бота: {e}")
        
        return None, None
    
    async def check_bot_token(self, token: str) -> bool:
        """Проверка валидности токена"""
        url = f'https://api.telegram.org/bot{token}/getMe'
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get('ok', False)
                    return False
        except Exception:
            return False
    
    async def check_internet_connection(self) -> bool:
        """Проверка интернет-соединения"""
        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            subprocess.check_output(
                ['ping', param, '1', '8.8.8.8'],
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return True
        except Exception:
            return False
    
    async def initialize_bot(self) -> bool:
        """Инициализация бота - основная логика"""
        if not await self.check_internet_connection():
            print("❌ Нет интернет-соединения. Проверьте подключение.")
            return False
        
        await self.client.start()
        me = await self.client.get_me()
        print(f"\n👤 Авторизован как: {me.first_name} (ID: {me.id})")
        
        # Проверяем наличие токена бота
        if not self.BOT_TOKEN_FILE.exists() or self.BOT_TOKEN_FILE.stat().st_size == 0:
            print("\n" + "🤖 НАСТРОЙКА БОТА".center(50, '─'))
            print("1. Создать нового бота")
            print("2. Загрузить существующего")
            print("─" * 50)
            
            choice = input("Выберите действие (1/2): ").strip()
            
            if choice == '2':
                username = input("Введите @username бота (без @): ").strip()
                if username:
                    result = await self.load_existing_bot(username)
                    if not result:
                        print("❌ Не удалось загрузить бота")
                        return False
                else:
                    print("❌ Не указано имя бота")
                    return False
            else:
                result = await self.create_new_bot()
                if not result:
                    print("❌ Не удалось создать бота")
                    return False
        else:
            # Проверяем существующий токен
            try:
                content = self.BOT_TOKEN_FILE.read_text().strip()
                if ':' in content:
                    parts = content.split(':')
                    if len(parts) >= 3:
                        token = ':'.join(parts[2:])
                        if not await self.check_bot_token(token):
                            print("❌ Токен недействителен")
                            return False
                    else:
                        print("❌ Неверный формат токена")
                        return False
            except Exception as e:
                print(f"❌ Ошибка чтения токена: {e}")
                return False
        
        return True
    
    async def run(self):
        """Основной цикл работы"""
        try:
            if await self.initialize_bot():
                print("\n" + "🚀 ЗАПУСК".center(50, '─'))
                print("Бот успешно инициализирован!")
                print("Загрузка модулей...")
                
                # Импортируем и запускаем модули
                try:
                    from core.modules import load_modules
                    await load_modules(self.client)
                    print("✅ Модули загружены")
                except ImportError as e:
                    print(f"⚠️ Ошибка загрузки модулей: {e}")
                
                print("\n" + "✅ ГОТОВО".center(50, '─'))
                print("Бот запущен и готов к работе!")
                print("Используйте .help для списка команд")
                print("─" * 50)
                
                await self.client.run_until_disconnected()
        
        except KeyboardInterrupt:
            print("\n🛑 Работа остановлена пользователем")
        except Exception as e:
            print(f"\n💥 Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
                print("\n🔌 Соединение закрыто")
