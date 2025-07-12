import os
import random
import string
import subprocess
import asyncio
import platform
import sys
from telethon import events, TelegramClient
from datetime import datetime, timedelta
import telethon
import requests
import pyfiglet
from langdetect import detect, DetectorFactory
import re
import importlib.util
from config import API_ID, API_HASH, BOT_TOKEN

# Инициализация
DetectorFactory.seed = 0
start_time = datetime.now()

# Глобальные переменные
received_messages_count = 0
sent_messages_count = 0
active_users = set()
MODS_DIRECTORY = 'source/mods/'
loaded_modules = []

client = TelegramClient(f'acroka_session_{API_ID}', API_ID, API_HASH)
GIF_URL = "https://tenor.com/vzU4iQebtgZ.gif"
GIF_FILENAME = "welcome.gif"
PREFIX_FILE = os.path.join('source', 'prefix.txt')
DEFAULT_PREFIX = '.'
RESTART_CMD = [sys.executable] + sys.argv

async def is_owner(event):
    """Проверяет, является ли отправитель владельцем сессии."""
    me = await event.client.get_me()
    return event.sender_id == me.id

async def load_all_modules(client):
    for module_file in os.listdir(MODS_DIRECTORY):
        if module_file.endswith('.py'):
            module_name = os.path.splitext(module_file)[0]
            module = await load_module(module_name)
            if module and hasattr(module, 'on_load'):
                await module.on_load(client)
                
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
        
def get_loaded_modules():
    modules = []
    if os.path.exists(MODS_DIRECTORY):
        for filename in os.listdir(MODS_DIRECTORY):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                modules.append(module_name)
    return modules


def get_prefix():
    """Получение текущего префикса команд"""
    if os.path.exists(PREFIX_FILE):
        with open(PREFIX_FILE, 'r') as f:
            prefix = f.read().strip()
            return prefix if len(prefix) == 1 else DEFAULT_PREFIX
    return DEFAULT_PREFIX

async def restart_bot(event=None):
    """Функция для перезапуска бота"""
    if event:
        await event.edit("🔄 Юзербот Акрока перезагружается, пожалуйста подождите...")
    print("🔄 Перезапуск юзербота...")
    os.execv(sys.executable, RESTART_CMD)

async def handle_help(event):
    if not await is_owner(event):
        return
    
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    modules_list = get_loaded_modules()
    prefix = get_prefix()
    base_commands = [
        f"📜 {prefix}info - информация о юзерботе",
        f"🏓 {prefix}ping - пинг системы",
        f"❓ {prefix}help - посмотреть команды",
        f"📦 {prefix}loadmod - загрузить модуль",
        f"🔄 {prefix}unloadmod - удалить модуль",
        f"⏳ {prefix}deferral - отложенные сообщения",
        f"🧮 {prefix}calc - калькулятор",
        f"💻 {prefix}tr - переводчик",
        f"🔄 {prefix}update - обновить бота",
        f"⚙️ {prefix}setprefix - изменить префикс команд",
        f"🔄 {prefix}restart - перезапустить юзербота"
    ]

    message = f"💡 Команды юзербота (префикс: '{prefix}')\n\n"
    if modules_list:
        message += "✅ Загруженные модули:\n"
        message += "\n".join(f"   - {get_module_info(m)}" for m in modules_list)
    else:
        message += "❌ Нет загруженных модулей.\n"
    
    message += "\n✅ Основные команды:\n" + "\n".join(base_commands)
    await event.edit(message)

async def handle_info(event):
    if not await is_owner(event):
        return
    
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
    if not await is_owner(event):
        return
    
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
    if not await is_owner(event):
        return
    
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
    if not await is_owner(event):
        return
    
    module_name = event.pattern_match.group(1)
    module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")
    
    if os.path.exists(module_path):
        os.remove(module_path)
        if module_name in loaded_modules:
            loaded_modules.remove(module_name)
        await event.edit(f"✅ Модуль '{module_name}' удалён")
    else:
        await event.edit(f"❌ Модуль '{module_name}' не найден")

async def translate_handler(event):
    if not await is_owner(event):
        return
    
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
        if not await is_owner(event):
            return
        
        global received_messages_count, active_users, sent_messages_count
        received_messages_count += 1
        active_users.add(event.sender_id)

        try:
            _, count, minutes, text = event.message.text.split(' ', 3)
            count = int(count)
            interval = int(minutes) * 60
        except:
            await event.edit(f"❗ Использование: {get_prefix()}deferral <кол-во> <мин> <текст>")
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
    if not await is_owner(event):
        return
    
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
    if not await is_owner(event):
        return
    
    try:
        await event.edit("🔄 Проверка обновлений юзербота...")
        repo = "https://github.com/ItKenneth/AcrokaUB.git"
        
        # Создаем временную директорию для обновления
        temp_dir = "temp_update"
        if os.path.exists(temp_dir):
            subprocess.run(['rm', '-rf', temp_dir])
        
        # Клонируем репозиторий
        subprocess.run(['git', 'clone', repo, temp_dir], check=True)
        
        # Проверяем наличие важных файлов
        required_files = ['modules.py', 'config.py', 'main.py']
        for file in required_files:
            if not os.path.exists(os.path.join(temp_dir, file)):
                raise Exception(f"Файл {file} не найден в обновлении")
        
        # Копируем файлы
        for file in required_files:
            src = os.path.join(temp_dir, file)
            if os.path.exists(src):
                os.replace(src, file)
        
        # Удаляем временную директорию
        subprocess.run(['rm', '-rf', temp_dir])
        
        await event.edit("✅ Юзербот успешно обновлен! Перезагрузка...")
        await restart_bot()
    except Exception as e:
        await event.edit(f"❌ Ошибка при обновлении: {str(e)}")
async def handle_setprefix(event):
    if not await is_owner(event):
        return
    
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    new_prefix = event.pattern_match.group(1).strip()
    
    if len(new_prefix) != 1:
        await event.edit("❌ Префикс должен быть одним символом!")
        return
    
    # Экранируем специальные символы регулярных выражений
    if new_prefix in r'\.^$*+?{}[]|()':
        new_prefix = '\\' + new_prefix
    
    try:
        os.makedirs('source', exist_ok=True)
        with open(PREFIX_FILE, 'w') as f:
            f.write(new_prefix.replace('\\', ''))  # Сохраняем без экранирования
        
        await event.edit(f"✅ Префикс изменён на '{new_prefix.replace('\\', '')}'! Перезагрузка...")
        await asyncio.sleep(2)
        await restart_bot()
    except Exception as e:
        await event.edit(f"❌ Ошибка при изменении префикса: {str(e)}")
    
async def handle_restart(event):
    if not await is_owner(event):
        return
    
    await restart_bot(event)

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

def register_event_handlers(client, prefix=None):
    if prefix is None:
        prefix = get_prefix()
    
    # Автоматическое экранирование спецсимволов в префиксе
    escaped_prefix = re.escape(prefix)
    
    deferred = DeferredMessage(client)
    
    handlers = [
        (rf'^{escaped_prefix}help$', handle_help),
        (rf'^{escaped_prefix}info$', handle_info),
        (rf'^{escaped_prefix}ping$', handle_ping),
        (rf'^{escaped_prefix}loadmod$', handle_loadmod),
        (rf'^{escaped_prefix}unloadmod (\w+)$', handle_unloadmod),
        (rf'^{escaped_prefix}tr (\w{{2}})$', translate_handler),
        (rf'^{escaped_prefix}calc (.+)$', calc_handler),
        (rf'^{escaped_prefix}deferral (\d+) (\d+) (.+)$', deferred.handler),
        (rf'^{escaped_prefix}update$', update_handler),
        (rf'^{escaped_prefix}setprefix (.+)$', handle_setprefix),
        (rf'^{escaped_prefix}restart$', handle_restart)
    ]

    for pattern, handler in handlers:
        client.add_event_handler(
            handler, 
            events.NewMessage(pattern=pattern, outgoing=True)
        )

async def run_bot(token):
    print(pyfiglet.figlet_format("Acroka"))
    print("🚀 Запуск бота...")
    
    try:
        await download_gif()

        bot_client = TelegramClient(f'acroka_bot_{API_ID}', API_ID, API_HASH)
        await bot_client.start(bot_token=token)
        
        # Передаем bot_client как аргумент
        await load_all_modules(client)  # <-- Ключевое исправление
        
        @bot_client.on(events.NewMessage(pattern='/start'))
        async def start_handler_internal(event):
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

        register_event_handlers(bot_client)
        print("✅ Бот запущен!")
        await bot_client.run_until_disconnected()

    except Exception as e:
        print(f"🛑 Критическая ошибка при запуске бота: {e}")
    finally:
        if 'bot_client' in locals() and bot_client.is_connected():
            await bot_client.disconnect()

def generate_username():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f'acroka_{random_part}_bot'

if __name__ == "__main__":
    asyncio.run(run_bot())
