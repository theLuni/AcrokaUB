import os
import random
import string
import subprocess
import asyncio
import platform
from telethon import events, TelegramClient
from datetime import datetime, timedelta
from config import TOKEN_FILE, API_ID, API_HASH
import telethon
import requests
import pyfiglet
from langdetect import detect, DetectorFactory
import re
import importlib.util
import subprocess
import os
import sys




# В начале файла
start_time = datetime.now()  # Сохраняем время старта

# Глобальные переменные для отслеживания статистики
received_messages_count = 0
sent_messages_count = 0
active_users = set()  # Храним уникальных пользователей

MODS_DIRECTORY = 'source/mods/'  #


client = TelegramClient('bot', API_ID, API_HASH)
 
loaded_modules = []  # Список загруженных модулей

# Функция для получения загруженных модулей



def get_module_info(module_name):
    """Возвращает информацию о модуле, если она имеется, анализируя первые строки файла."""
    try:
        module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")
        with open(module_path, 'r', encoding='utf-8') as f:
            # Считываем первые четыре строки
            lines = [f.readline().strip() for _ in range(4)]

        # Инициализация значений
        name = "Неизвестно"
        commands = "Неизвестно"

        # Извлечение информации из строк
        for line in lines:
            if line.startswith("#"):
                key, value = line[1:].split(":", 1)  # Разделяем на ключ и значение
                if key.strip() == "name":
                    name = value.strip()
                elif key.strip() == "commands":
                    commands = value.strip()
        
        return f"{name} ({commands})"

    except Exception as e:
        print(f"Ошибка при получении информации о модуле {module_name}: {e}")
        return None
        
def get_loaded_modules():
    modules = []
    if os.path.exists(MODS_DIRECTORY):
        for filename in os.listdir(MODS_DIRECTORY):
            if filename.endswith(".py"):
                module_name = filename[:-3]  # Убираем ".py"
                modules.append(module_name)
    return modules


async def handle_help(event):
    modules_list = get_loaded_modules()
    commands_list = [
        "📜 info - информация о юзерботе",
        "🏓 ping - пинг системы",
        "❓ help - посмотреть команды",
        "📦 loadmod - загрузить модуль",
        "🔄 unloadmod - удалить модуль",
        "📜 modload - выгрузить модуль",
        "⏳ deferral - поставить отложенные сообщения",
        "🧮 calc - калькулятор\n"
        "💻 tr - переводчик"
    ]

    # Создаем основной текст сообщения
    new_message_text = "💡 Команды юзербота\n\n"

    # Создаем список загруженных модулей
    if modules_list:
        new_message_text += "✅ Загруженные модули:\n"
        for module in modules_list:
            module_info = get_module_info(module)
            if module_info:
                new_message_text += f"   - {module_info}\n"
    else:
        new_message_text += "❌ В данный момент нет загруженных модулей."

    # Добавляем доступные команды
    new_message_text += "\n✅ Доступные команды:\n"
    new_message_text += "\n".join(commands_list)

    # Отправляем готовое сообщение
    try:
        await event.message.edit(new_message_text)
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")

async def load_module(module_name):
    try:
        module_spec = importlib.util.spec_from_file_location(module_name, os.path.join(MODS_DIRECTORY, f"{module_name}.py"))
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        loaded_modules.append(module_name)
        return module  # Возвращаем загруженный модуль
    except Exception as e:
        print(f"Ошибка при загрузке модуля {module_name}: {e}")
        return None

# Функция для обработки команды .loadmod
async def handle_loadmod(event, client):
    replied_message = await event.get_reply_message()
    if replied_message and replied_message.media:
        file = await replied_message.download_media(file=MODS_DIRECTORY)
        module_name = os.path.splitext(os.path.basename(file))[0]

        module = await load_module(module_name)
        
        if module:
            new_message_text = f"✅ Модуль '{module_name}' успешно загружен!"
            # Вызываем on_load, если она существует
            if hasattr(module, 'on_load'):
                await module.on_load(client)  # Используем client вместо bot_client
        else:
            new_message_text = f"❌ Не удалось загрузить модуль '{module_name}'."
    else:
        new_message_text = "❌ Пожалуйста, ответьте на сообщение с файлом .py для загрузки модуля."

    # Изменяем текст самого сообщения команды .loadmod
    try:
        await event.message.edit(new_message_text)
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")

async def load_all_modules(client):
    for module_file in os.listdir(MODS_DIRECTORY):
        if module_file.endswith('.py'):
            module_name = os.path.splitext(module_file)[0]
            module = await load_module(module_name)
            if module and hasattr(module, 'on_load'):
                await module.on_load(client)  # Вызов

# Функция для обработки команды .unloadmod
async def handle_unloadmod(event, module_name):
    module_path = os.path.join(MODS_DIRECTORY, f"{module_name}.py")

    if os.path.isfile(module_path):
        os.remove(module_path)  # Удаляем файл
        new_message_text = f"✅ Модуль '{module_name}' был успешно удалён."
    else:
        new_message_text = f"❌ Модуль '{module_name}' не найден."

    # Изменяем текст сообщения
    try:
        await event.message.edit(new_message_text)
    except Exception as e:
        print(f"Ошибка при редактировании сообщения: {e}")

DetectorFactory.seed = 0


def translate_text(text, target_lang):
    # Список допустимых языковых пар
    valid_languages = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'zh-CN': 'Chinese (Simplified)',
        'ru': 'Russian',
    }

    # Проверяем, есть ли указанный язык в списке
    if target_lang not in valid_languages:
        return f"Ошибка: неверный код языка '{target_lang}'. Пожалуйста, используйте двухбуквенные коды ISO, например: 'en', 'ru' и т.д."

    # Формируем URL для API перевода с указанным языком оригинала и целевым языком
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={detect(text)}|{target_lang}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP
        data = response.json()

        # Проверяем, есть ли ошибка в ответе
        if "responseData" in data and "translatedText" in data["responseData"]:
            return data["responseData"]["translatedText"]
        else:
            return "Ошибка перевода: не удалось получить ответ от API."
    except Exception as e:
        return f"Ошибка перевода: {str(e)}."

async def translate_handler(event):
    global received_messages_count, active_users
    received_messages_count += 1
    active_users.add(event.sender_id)

    if event.is_reply:
        target_language = event.message.text.split(' ')[1].strip()  # Только код языка из сообщения
        replied_message = await event.get_reply_message()  # Получаем сообщение, на которое отвечаем
        
        if replied_message:
            text_to_translate = replied_message.message  # Текст для перевода - это текст ответного сообщения

            # Переводим текст
            translated_text = translate_text(text_to_translate, target_language)

            # Изменяем сообщение с командой на переведённый текст
            await event.message.edit(translated_text)  # Редактируем сообщение с командой
        else:
            await event.reply("❌ Ошибка: Не удалось получить сообщение для перевода.")
    else:
        await event.reply("❗️ Используйте эту команду в ответ на сообщение, которое нужно перевести.")

class DeferredMessage:
    def __init__(self, client):
        self.client = client
        self.interval = 3600  # По умолчанию, 1 час
        self.message_count = 10  # По умолчанию, 10 сообщений
        self.sent_message_id = None  # ID отправленного сообщения

    async def отложка(self, event):
        global sent_messages_count
        args = event.message.message.split(' ', 3)

        if len(args) < 4:
            await event.reply("❗️ Пожалуйста, укажите количество сообщений, период (в минутах) и текст.")
            return
        
        try:
            self.message_count = int(args[1].strip())
            self.interval = int(args[2].strip()) * 60  # Конвертируем минуты в секунды
        except ValueError:
            await event.reply("❌ Пожалуйста, укажите корректные числовые значения.")
            return
        
        text = args[3].strip()
        
        if not text:
            await event.reply("✋ Пожалуйста, укажите текст сообщения.")
            return

        self.sent_message_id = await event.reply(f"✅ Сообщения успешно запланированы!\n\n"
                                                  f"📅 Запланировано отправить {self.message_count} сообщений с интервалом в {self.interval // 60} минут(ы).")

        chat_id = event.chat_id
        
        for i in range(self.message_count):
            send_time = datetime.now() + timedelta(seconds=self.interval * i)
            await self.client.send_message(chat_id, text, schedule=send_time)
            sent_messages_count += 1  # Увеличиваем счётчик отправленных сообщений
            
            # Обновляем сообщение с информацией о статусе
            await self.client.edit_message(
                chat_id,
                self.sent_message_id,
                f"📬 Сообщение {i + 1}/{self.message_count} отправлено! "
                f"Следующее через {self.interval // 60} минут(ы)."
            )

    async def handler(self, event):
        global received_messages_count, active_users
        received_messages_count += 1  # Увеличиваем счётчик полученных сообщений
        active_users.add(event.sender_id)  # Добавляем пользователя в активные пользователи
        await self.отложка(event)  # Вызов метода отложка

async def calc_handler(event):
    # Извлекаем математическое выражение из сообщения
    expression = event.message.text.split('.calc ')[1].strip()  # Получаем выражение после команды

    # Удаляем все символы, кроме цифр, операторов и пробелов, чтобы избежать ошибок
    valid_expression = re.sub(r'[^0-9+\-*/. ()]', '', expression)
    
    try:
        # Вычисляем результат
        result = eval(valid_expression)
        # Редактируем сообщение с командой на результат
        await event.message.edit(f"💡 Результат: {result}")
    except Exception as e:
        # В случае ошибки редактируем сообщение с командой на сообщение об ошибке
        await event.message.edit(f"❌ Ошибка в вычислении: {str(e)}")



def register_event_handlers(client):
    deferred_message = DeferredMessage(client) 
    @client.on(events.NewMessage(pattern=r'\.modload (\w+)'))
    async def modload_command(event):
        module_name = event.pattern_match.group(1)

    # Определяем путь к модулю
        module_path = f"source.mods.{module_name}"

        try:
        # Загружаем модуль
            importlib.import_module(module_path)

        # Отправляем сообщение о том, что модуль успешно загружен
            await event.reply(f"✅ Модуль `{module_name}` успешно загружен!")
        except ModuleNotFoundError:
        # Если модуль не найден
            await event.reply(f"❌ Модуль `{module_name}` не найден.")
        except Exception as e:
        # Обработка других ошибок
            await event.reply(f"❌ Ошибка при загрузке модуля `{module_name}`: {str(e)}")
    @client.on(events.NewMessage(pattern=r'\.update'))
    async def update_handler(event):
        # URL репозитория на GitHub от ItKenneth
        repository_url = 'https://github.com/ItKenneth/AcrokaUB.git'
        
        # Путь, куда будет клонироваться репозиторий
        repo_directory = '/AcrokaUB'
        # Путь к проекту (возможно, тоже '/AcrokaUB', если файлы напрямую там)
        project_directory = '/AcrokaUB'  # Если файлы будут обновлены в том же каталоге

        # Файлы для обновления
        files_to_update = ['modules.py', 'config.py', 'main.py']

        try:
            # Проверка, существует ли директория репозитория
            if not os.path.exists(repo_directory):
                await event.reply("Клонирование репозитория...")
                subprocess.run(['git', 'clone', repository_url, repo_directory], check=True)  # Клонирование
                await event.reply(f"Репозиторий успешно клонирован в {repo_directory}.")
            else:
                await event.reply("Обновление репозитория...")
                subprocess.run(['git', '-C', repo_directory, 'pull'], check=True)  # Обновление репозитория
                await event.reply("Репозиторий успешно обновлен.")

            # Обновление файлов
            for file_name in files_to_update:
                source_file_path = os.path.join(repo_directory, file_name)
                destination_file_path = os.path.join(project_directory, file_name)  # Путь к папке вашего проекта
            
                # Проверка, существует ли файл
                if os.path.exists(source_file_path):
                    await event.reply(f"Обновление файла {file_name}...")
                    # Перемещаем файл (заменяем существующий)
                    os.replace(source_file_path, destination_file_path)
                    await event.reply(f"Файл {file_name} успешно обновлён.")
                else:
                    await event.reply(f"Ошибка: файл {file_name} не найден в репозитории.")
            
            await event.reply("Обновление завершено. Перезапуск скрипта...")
            
            # Перезапуск скрипта
            os.execv(sys.executable, ['python'] + sys.argv)
        
        except subprocess.CalledProcessError as err:
            await event.reply(f"Ошибка при выполнении команды: {err}")
        except Exception as e:
            await event.reply(f"Ошибка: {str(e)}")
    
    @client.on(events.NewMessage(pattern=r'\.deferral'))
    async def handler(event):  # Добавляем пользователя в активные пользователи
        await deferred_message.handler(event)

    @client.on(events.NewMessage(pattern=r'\.tr (\w{2})'))
    async def handler(event):
        await translate_handler(event)
    @client.on(events.NewMessage(pattern=r'\.calc (.+)'))
    async def handler(event):
        await calc_handler(event)    
    @client.on(events.NewMessage(pattern=r'\.unloadmod (\w+)'))   
    async def unloadmod_handler(event):
        module_name = event.message.text.split()[1]  # Получаем название модуля
        await handle_unloadmod(event, module_name)
              # Передаем event и имя модуля         

    @client.on(events.NewMessage(pattern=r'\.loadmod', func=lambda e: e.is_reply and e.reply_to_msg_id is not None))
    async def loadmod_handler(event):
        await handle_loadmod(event, client)
        
    @client.on(events.NewMessage(pattern=r'\.help'))
    async def help_handler(event):
    	await handle_help(event)  # Вызов функции обработки помощи    
    @client.on(events.NewMessage(pattern=r'\.info'))
    async def info_handler(event):
        uptime = datetime.now() - start_time  # Рассчитываем время работы 
        uptime_str = str(uptime).split('.')[0]  # Убираем миллисекунды

        device = platform.system()
        user_name = event.sender.first_name  # Имя владельца аккаунта
        current_status = "Активен"  # Устанавливаем текущий статус
        info_message = (
            f"🔍 Acroka - UserBot:\n\n"
            f"👤 Владелец {user_name}\n"
            f"💻 Платформа: {device}\n"
            f"⏳ Uptime: {uptime_str}\n"
            f"✨ Версия Telethon: {telethon.__version__}\n" 
            f"📥 Sent: {received_messages_count}\n"
            f"📤 Accepted: {sent_messages_count}\n"
            f"🟢 Статус: {current_status}\n"
            f"👥 Количество активных пользователей: {len(active_users)}\n"
        )

        await event.edit(info_message)

    @client.on(events.NewMessage(pattern=r'\.ping'))
    async def ping_handler(event):
        process = subprocess.Popen(['ping', '-c', '1', 'google.com'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            result = "✅ Пинг к Google: Время: {}мс".format(stdout.decode().split('time=')[1].split(' ')[0])
        else:
            result = "❌ Ошибка пинга!"

        await event.edit(result)

def generate_username():
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    return f'acroka_{random_part}_bot'
        
GIF_URL = "https://tenor.com/vzU4iQebtgZ.gif"  # Новый URL GIF
GIF_FILENAME = "welcome.gif"  # Имя файла для сохранения

async def download_gif(url, filename):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print("GIF изображение успешно загружено и сохранено.")
        else:
            print("Не удалось загрузить GIF изображение. Код ответа:", response.status_code)
    except Exception as e:
        print("Ошибка при загрузке GIF:", str(e))

async def run_bot(client, token):
    # Генерация ASCII-арта
    ascii_art = pyfiglet.figlet_format("Acroka")
    print(ascii_art)  # Выводим ASCII-арт в консоль

    # Сообщение о запуске
    print("Запуск Acroka...")

    # Проверяем, существует ли файл с GIF-картинкой
    if not os.path.exists(GIF_FILENAME):
        await download_gif(GIF_URL, GIF_FILENAME)

    bot_client = TelegramClient('bot', API_ID, API_HASH)
    await bot_client.start(bot_token=token)
    await load_all_modules(client)

    # Уведомление о том, что бот запущен
    print("Бот успешно запущен и готов к работе!")

    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        # Отправляем GIF при первом запуске с текстом
        await bot_client.send_file(
            event.chat_id,
            GIF_FILENAME,
            caption=(
                '👋 Привет! Я - Acroka - userbot!\n'
                '📅 Для просмотра основных команд используй .info.\n\n'
                '💬 Если тебе нужна поддержка, пиши: [Акрока Саппорт](https://t.me/acroka_support)'
            ),
            parse_mode='markdown'  # Поддержка Markdown для форматирования
        )

    print("Бот готов к прослушиванию сообщений...")
    
    await bot_client.run_until_disconnected()
    print("Бот отключен.")
