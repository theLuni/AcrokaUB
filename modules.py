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
from config import API_ID, API_HASH

# Инициализация
DetectorFactory.seed = 0
start_time = datetime.now()

# Глобальные переменные
received_messages_count = 0
sent_messages_count = 0
active_users = set()
MODS_DIRECTORY = 'source/mods/'
loaded_modules = []

client = TelegramClient('acroka_session', API_ID, API_HASH)
GIF_URL = "https://tenor.com/vzU4iQebtgZ.gif"
GIF_FILENAME = "welcome.gif"

def get_module_info(module_name):
    try:
        module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")
        with open(module_path, 'r', encoding='utf-8') as f:
            lines = [f.readline().strip() for _ in range(4)]

        name = commands = "Неизвестно"
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

async def handle_help(event):
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    modules_list = get_loaded_modules()
    base_commands = [
        "📜 info - информация о юзерботе",
        "🏓 ping - пинг системы",
        "❓ help - посмотреть команды",
        "📦 loadmod - загрузить модуль",
        "🔄 unloadmod - удалить модуль",
        "⏳ deferral - отложенные сообщения",
        "🧮 calc - калькулятор",
        "💻 tr - переводчик",
        "🔄 update - обновить бота"
    ]

    message = "💡 Команды юзербота\n\n"
    if modules_list:
        message += "✅ Загруженные модули:\n"
        message += "\n".join(f"   - {get_module_info(m)}" for m in modules_list)
    else:
        message += "❌ Нет загруженных модулей.\n"
    
    message += "\n✅ Основные команды:\n" + "\n".join(base_commands)
    await event.message.edit(message)

async def handle_info(event):
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    uptime = str(datetime.now() - start_time).split('.')[0]
    user_name = (await event.client.get_me()).first_name
    
    info_msg = (
        f"🔍 Acroka - UserBot\n\n"
        f"👤 Владелец: {user_name}\n"
        f"💻 Платформа: {platform.system()}\n"
        f"⏳ Время работы: {uptime}\n"
        f"✨ Telethon: {telethon.__version__}\n"
        f"📥 Получено: {received_messages_count}\n"
        f"📤 Отправлено: {sent_messages_count}\n"
        f"👥 Пользователей: {len(active_users)}\n"
        f"🟢 Статус: Активен"
    )
    await event.edit(info_msg)

async def handle_ping(event):
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    try:
        proc = await asyncio.create_subprocess_exec(
            'ping', '-c', '1', 'google.com',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        
        if proc.returncode == 0:
            time = stdout.decode().split('time=')[1].split()[0]
            await event.edit(f"✅ Пинг: {time}")
        else:
            await event.edit("❌ Ошибка пинга!")
    except Exception as e:
        await event.edit(f"❌ Ошибка: {str(e)}")

async def load_module(module_name):
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, 
            os.path.join(MODS_DIRECTORY, f"{module_name}.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if module_name not in loaded_modules:
            loaded_modules.append(module_name)
            if hasattr(module, 'on_load'):
                await module.on_load(client)
        return module
    except Exception as e:
        print(f"Ошибка загрузки модуля {module_name}: {e}")
        return None

async def handle_loadmod(event):
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply.media:
            file = await reply.download_media(MODS_DIRECTORY)
            module_name = os.path.splitext(os.path.basename(file))[0]
            
            if await load_module(module_name):
                await event.edit(f"✅ Модуль '{module_name}' загружен!")
            else:
                await event.edit(f"❌ Ошибка загрузки '{module_name}'")
            return
    
    await event.edit("❌ Ответьте на сообщение с файлом .py")

async def handle_unloadmod(event):
    module_name = event.pattern_match.group(1)
    module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")
    
    if os.path.exists(module_path):
        os.remove(module_path)
        await event.edit(f"✅ Модуль '{module_name}' удалён")
    else:
        await event.edit(f"❌ Модуль '{module_name}' не найден")

async def translate_handler(event):
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    if not event.is_reply:
        await event.reply("❗ Ответьте на сообщение для перевода")
        return
    
    target_lang = event.pattern_match.group(1)
    replied = await event.get_reply_message()
    
    try:
        url = f"https://api.mymemory.translated.net/get?q={replied.text}&langpair={detect(replied.text)}|{target_lang}"
        response = requests.get(url).json()
        translated = response['responseData']['translatedText']
        await event.edit(translated)
    except Exception as e:
        await event.edit(f"❌ Ошибка перевода: {str(e)}")

class DeferredMessage:
    def __init__(self, client):
        self.client = client
    
    async def handler(self, event):
        global received_messages_count, active_users, sent_messages_count
        received_messages_count += 1
        active_users.add(event.sender_id)

        try:
            _, count, minutes, text = event.message.text.split(' ', 3)
            count = int(count)
            interval = int(minutes) * 60
        except:
            await event.edit("❗ Использование: .deferral <кол-во> <мин> <текст>")
            return

        msg = await event.reply(f"✅ Запланировано {count} сообщений с интервалом {minutes} мин")
        
        for i in range(count):
            send_time = datetime.now() + timedelta(seconds=interval*i)
            await self.client.send_message(
                event.chat_id, 
                text, 
                schedule=send_time
            )
            sent_messages_count += 1
            await msg.edit(f"📬 Отправлено {i+1}/{count}")

async def calc_handler(event):
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    expr = re.sub(r'[^0-9+\-*/. ()]', '', event.pattern_match.group(1))
    try:
        result = eval(expr)
        await event.edit(f"💡 Результат: {result}")
    except Exception as e:
        await event.edit(f"❌ Ошибка: {str(e)}")

async def update_handler(event):
    try:
        await event.edit("🔄 Обновление бота...")
        repo = "https://github.com/ItKenneth/AcrokaUB.git"
        
        if not os.path.exists('AcrokaUB'):
            subprocess.run(['git', 'clone', repo, 'AcrokaUB'], check=True)
        else:
            subprocess.run(['git', '-C', 'AcrokaUB', 'pull'], check=True)
        
        for file in ['modules.py', 'config.py', 'main.py']:
            src = os.path.join('AcrokaUB', file)
            if os.path.exists(src):
                os.replace(src, file)
        
        await event.edit("✅ Обновлено! Перезапуск...")
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        await event.edit(f"❌ Ошибка: {str(e)}")

async def load_all_modules():
    if os.path.exists(MODS_DIRECTORY):
        for file in os.listdir(MODS_DIRECTORY):
            if file.endswith('.py'):
                await load_module(file[:-3])

async def download_gif():
    if not os.path.exists(GIF_FILENAME):
        try:
            response = requests.get(GIF_URL, stream=True)
            if response.status_code == 200:
                with open(GIF_FILENAME, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
        except Exception as e:
            print(f"Ошибка загрузки GIF: {e}")

async def run_bot(token):
    print(pyfiglet.figlet_format("Acroka"))
    print("🚀 Запуск бота...")
    
    try:
        await download_gif()
        await load_all_modules()

        bot_client = TelegramClient('acroka_bot', API_ID, API_HASH)
        await bot_client.start(bot_token=token)

        @bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            try:
                if os.path.exists(GIF_FILENAME):
                    await bot_client.send_file(
                        event.chat_id,
                        GIF_FILENAME,
                        caption='👋 Привет! Я - Acroka UserBot!\n📌 Используй .help для списка команд',
                        parse_mode='markdown'
                    )
                else:
                    await event.respond('👋 Привет! Я - Acroka UserBot!')
            except Exception as e:
                print(f"⚠️ Ошибка при обработке /start: {e}")

        print("✅ Бот запущен!")
        await bot_client.run_until_disconnected()

    except Exception as e:
        print(f"🛑 Критическая ошибка при запуске бота: {e}")
    finally:
        if 'bot_client' in locals() and bot_client.is_connected():
            await bot_client.disconnected()
            
def register_event_handlers(client):
    deferred = DeferredMessage(client)

    handlers = [
        (r'\.help$', handle_help),
        (r'\.info$', handle_info),
        (r'\.ping$', handle_ping),
        (r'\.loadmod$', handle_loadmod),
        (r'\.unloadmod (\w+)', handle_unloadmod),
        (r'\.tr (\w{2})$', translate_handler),
        (r'\.calc (.+)', calc_handler),
        (r'\.deferral', deferred.handler),
        (r'\.update$', update_handler)
    ]

    for pattern, handler in handlers:
        client.add_event_handler(
            handler, 
            events.NewMessage(pattern=pattern)
        )

def generate_username():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f'acroka_{random_part}_bot'
