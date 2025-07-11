import os
import random
import string
import subprocess
import asyncio
import platform
from telethon import events, TelegramClient
from datetime import datetime, timedelta
import telethon
import requests
import pyfiglet
from langdetect import detect, DetectorFactory
import re
import importlib.util
import aiohttp
import sys

# Инициализация детектора языка
DetectorFactory.seed = 0

# Конфигурационные параметры
MODS_DIRECTORY = 'source/mods/'
TOKEN_FILE = 'source/bottoken.txt'
BOT_IMAGE = 'source/pic.png'
GIF_URL = "https://tenor.com/vzU4iQebtgZ.gif"
GIF_FILENAME = "welcome.gif"

# Статистика
start_time = datetime.now()
received_messages_count = 0
sent_messages_count = 0
active_users = set()
loaded_modules = []

class AcrokaClient:
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None
        self.bot_client = None
        self.me = None
        
    async def initialize(self):
        """Инициализация клиента и получение информации о пользователе"""
        # Создаем временную сессию для получения ID пользователя
        temp_client = TelegramClient('temp_session', self.api_id, self.api_hash)
        await temp_client.start()
        self.me = await temp_client.get_me()
        await temp_client.disconnect()
        
        # Создаем основного клиента с именем сессии на основе ID пользователя
        session_name = f'acroka_{self.me.id}'
        self.client = TelegramClient(session_name, self.api_id, self.api_hash)
        
        # Проверяем и создаем необходимые директории
        os.makedirs(MODS_DIRECTORY, exist_ok=True)
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        
    async def setup_bot(self):
        """Настройка бота через BotFather"""
        if not os.path.exists(TOKEN_FILE) or os.stat(TOKEN_FILE).st_size == 0:
            choice = input("Файл токена пуст. Хотите загрузить существующего бота? (да/нет): ").strip().lower()
            
            if choice == 'да':
                username = input("Введите юзернейм вашего бота (без @): ").strip()
                token_data = await self.get_existing_bot(username)
                
                if token_data:
                    with open(TOKEN_FILE, 'w') as f:
                        f.write(token_data)
                else:
                    print("Не удалось получить токен от @BotFather.")
                    return False
            else:
                print("Создаем нового бота...")
                token_data = await self.create_new_bot()
                if not token_data:
                    return False
        
        return True
    
    async def get_existing_bot(self, username):
        """Получение токена существующего бота"""
        botfather = await self.client.get_input_entity('BotFather')
        
        await self.client.send_message(botfather, '/token')
        await asyncio.sleep(2)
        await self.client.send_message(botfather, f'@{username}')
        await asyncio.sleep(2)
        
        async for message in self.client.iter_messages(botfather, limit=10):
            if "You can use this token to access HTTP API:" in message.text:
                token = message.text.split("You can use this token to access HTTP API:")[1].strip().split()[0].replace("`", "")
                
                # Установка аватарки
                await self.set_bot_photo(username)
                
                return f"{username}:{token.split(':')[0]}:{token}"
        
        return None
    
    async def create_new_bot(self):
        """Создание нового бота"""
        botfather = await self.client.get_input_entity('BotFather')
        bot_title = 'Acroka'
        username = f'acroka_{"".join(random.choices(string.ascii_lowercase + string.digits, k=5))}_bot'
        
        try:
            await self.client.send_message(botfather, '/newbot')
            await asyncio.sleep(2)
            await self.client.send_message(botfather, bot_title)
            await asyncio.sleep(2)
            await self.client.send_message(botfather, username)
            await asyncio.sleep(5)
            
            token = None
            async for message in self.client.iter_messages(botfather, limit=10):
                if 'Use this token to access the HTTP API:' in message.message:
                    token = message.message.split('\n')[1].strip()
                    break
            
            if not token:
                print("Не удалось получить токен от BotFather.")
                return None
            
            # Установка аватарки
            await self.set_bot_photo(username)
            
            # Сохраняем данные бота
            data = f"{username}:{token.split(':')[0]}:{token}"
            with open(TOKEN_FILE, 'w') as f:
                f.write(data)
                
            return data
        except Exception as e:
            print(f"Ошибка при создании бота: {e}")
            return None
    
    async def set_bot_photo(self, username):
        """Установка фото для бота"""
        if os.path.exists(BOT_IMAGE):
            botfather = await self.client.get_input_entity('BotFather')
            await self.client.send_message(botfather, '/setuserpic')
            await asyncio.sleep(2)
            await self.client.send_message(botfather, f'@{username}')
            await asyncio.sleep(2)
            await self.client.send_file(botfather, BOT_IMAGE)
        else:
            print(f"Файл аватарки {BOT_IMAGE} не найден.")
    
    async def download_gif(self):
        """Загрузка приветственного GIF"""
        if not os.path.exists(GIF_FILENAME):
            try:
                response = requests.get(GIF_URL, stream=True)
                if response.status_code == 200:
                    with open(GIF_FILENAME, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
            except Exception as e:
                print(f"Ошибка при загрузке GIF: {e}")
    
    async def load_module(self, module_name):
        """Загрузка модуля"""
        try:
            module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if module_name not in loaded_modules:
                loaded_modules.append(module_name)
                
            if hasattr(module, 'on_load'):
                await module.on_load(self)
                
            return module
        except Exception as e:
            print(f"Ошибка при загрузке модуля {module_name}: {e}")
            return None
    
    async def load_all_modules(self):
        """Загрузка всех модулей из директории"""
        if os.path.exists(MODS_DIRECTORY):
            for filename in os.listdir(MODS_DIRECTORY):
                if filename.endswith(".py"):
                    module_name = filename[:-3]
                    await self.load_module(module_name)
    
    def get_module_info(self, module_name):
        """Получение информации о модуле"""
        try:
            module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")
            with open(module_path, 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(4)]
            
            name = "Неизвестно"
            commands = "Неизвестно"
            
            for line in lines:
                if line.startswith("#"):
                    key, value = line[1:].split(":", 1)
                    if key.strip() == "name":
                        name = value.strip()
                    elif key.strip() == "commands":
                        commands = value.strip()
            
            return f"{name} ({commands})"
        except Exception:
            return f"{module_name} (Неизвестно)"
    
    async def handle_help(self, event):
        """Обработка команды .help"""
        global received_messages_count, active_users
        received_messages_count += 1
        active_users.add(event.sender_id)
        
        modules_list = [f[:-3] for f in os.listdir(MODS_DIRECTORY) if f.endswith(".py")] if os.path.exists(MODS_DIRECTORY) else []
        
        commands_list = [
            "📜 info - информация о юзерботе",
            "🏓 ping - пинг системы",
            "❓ help - посмотреть команды",
            "📦 loadmod - загрузить модуль",
            "🔄 unloadmod - удалить модуль",
            "📜 modload - выгрузить модуль",
            "⏳ deferral - поставить отложенные сообщения",
            "🧮 calc - калькулятор",
            "💻 tr - переводчик"
        ]
        
        message = "💡 Команды юзербота\n\n"
        
        if modules_list:
            message += "✅ Загруженные модули:\n"
            for module in modules_list:
                module_info = self.get_module_info(module)
                message += f"   - {module_info}\n"
        else:
            message += "❌ Нет загруженных модулей.\n"
        
        message += "\n✅ Доступные команды:\n" + "\n".join(commands_list)
        
        try:
            await event.message.edit(message)
        except Exception as e:
            print(f"Ошибка при редактировании сообщения: {e}")
    
    async def handle_info(self, event):
        """Обработка команды .info"""
        global received_messages_count, active_users
        received_messages_count += 1
        active_users.add(event.sender_id)
        
        uptime = datetime.now() - start_time
        uptime_str = str(uptime).split('.')[0]
        
        info_message = (
            f"🔍 Acroka - UserBot:\n\n"
            f"👤 Владелец: {self.me.first_name}\n"
            f"💻 Платформа: {platform.system()}\n"
            f"⏳ Uptime: {uptime_str}\n"
            f"✨ Версия Telethon: {telethon.__version__}\n" 
            f"📥 Получено сообщений: {received_messages_count}\n"
            f"📤 Отправлено сообщений: {sent_messages_count}\n"
            f"👥 Активных пользователей: {len(active_users)}\n"
        )
        
        await event.edit(info_message)
    
    async def handle_ping(self, event):
        """Обработка команды .ping"""
        global received_messages_count, active_users
        received_messages_count += 1
        active_users.add(event.sender_id)
        
        try:
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', 'google.com',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                time = stdout.decode().split('time=')[1].split(' ')[0]
                await event.edit(f"✅ Пинг к Google: {time}мс")
            else:
                await event.edit("❌ Ошибка пинга!")
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")
    
    async def register_handlers(self):
        """Регистрация обработчиков событий"""
        @self.client.on(events.NewMessage(pattern=r'\.help'))
        async def handler(event):
            await self.handle_help(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.info'))
        async def handler(event):
            await self.handle_info(event)
        
        @self.client.on(events.NewMessage(pattern=r'\.ping'))
        async def handler(event):
            await self.handle_ping(event)
        
        # Другие обработчики...
    
    async def run(self):
        """Запуск клиента"""
        await self.initialize()
        
        if not await self.setup_bot():
            return
        
        await self.download_gif()
        await self.load_all_modules()
        await self.register_handlers()
        
        # Запускаем бота
        with open(TOKEN_FILE, 'r') as f:
            _, _, token = f.read().strip().split(':', 2)
        
        self.bot_client = TelegramClient(f'acroka_bot_{self.me.id}', self.api_id, self.api_hash)
        await self.bot_client.start(bot_token=token)
        
        @self.bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await self.bot_client.send_file(
                event.chat_id,
                GIF_FILENAME,
                caption=(
                    '👋 Привет! Я - Acroka - userbot!\n'
                    '📅 Для просмотра основных команд используй .info.\n\n'
                    '💬 Если тебе нужна поддержка, пиши: [Акрока Саппорт](https://t.me/acroka_support)'
                ),
                parse_mode='markdown'
            )
        
        print(pyfiglet.figlet_format("Acroka"))
        print("Бот успешно запущен и готов к работе!")
        
        await asyncio.gather(
            self.client.run_until_disconnected(),
            self.bot_client.run_until_disconnected()
        )

if __name__ == '__main__':
    # Получаем API_ID и API_HASH из config.py или переменных окружения
    try:
        from config import API_ID, API_HASH
    except ImportError:
        API_ID = os.getenv('API_ID')
        API_HASH = os.getenv('API_HASH')
    
    if not API_ID or not API_HASH:
        print("Ошибка: необходимо указать API_ID и API_HASH в config.py или переменных окружения")
        sys.exit(1)
    
    client = AcrokaClient(API_ID, API_HASH)
    asyncio.run(client.run())