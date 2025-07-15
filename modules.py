from typing import Dict, Any
import os
import sys
import subprocess 
import importlib
import asyncio
import re
import shutil
from bs4 import BeautifulSoup
import traceback
import platform
import telethon
import psutil
import socket
import uuid
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import Message
from config import API_ID, API_HASH
import requests
from googletrans import Translator

# Константы
MODS_DIR = 'source/mods/'
PREFIX_FILE = 'source/prefix.txt'
DEFAULT_PREFIX = '.'
LOADED_MODS_FILE = '.loaded_mods'
SESSION_FILE = 'userbot_session'
GITHUB_REPO = "https://github.com/theLuni/AcrokaUB"
MODS_REPO = "https://github.com/theLuni/AcrokaUB-Modules"
RAW_MODS_URL = "https://raw.githubusercontent.com/theLuni/AcrokaUB-Modules/main/"
DOCS_URL = "https://github.com/theLuni/AcrokaUB/wiki"
BACKUP_DIR = 'source/backups/'
LOG_FILE = 'userbot.log'
# constants.py
CUSTOM_INFO_FILE = 'source/custom_info.json'

DEFAULT_INFO_TEMPLATE = """🤖 <b>Acroka UserBot v{version}</b>
🔹 <b>Сессия:</b> <code>{session_id}</code>
🔹 <b>Обновлено:</b> <code>{last_update_time}</code>

👤 <b>Владелец:</b> <a href='tg://user?id={owner_id}'>{owner_name}</a>
🆔 <b>ID:</b> <code>{owner_id}</code>
⏱ <b>Аптайм:</b> {uptime}
📦 <b>Модулей:</b> {modules_count}

⚙️ <b>Система:</b>
• <b>ОС:</b> {os_info}
• <b>Python:</b> {python_version}
• <b>Telethon:</b> {telethon_version}

💻 <b>Ресурсы:</b>
• <b>CPU:</b> {cpu_usage}% ({cpu_cores} ядер)
• <b>RAM:</b> {ram_percent}% ({ram_used}/{ram_total} MB)

📂 <b>Репозиторий:</b> <code>{repo_url}</code>"""

class ModuleFinder:
    def __init__(self, repo_url):
        self.repo_url = repo_url
        self.modules_db_url = f"{RAW_MODS_URL}modules_db.json"
        self.modules = self._load_modules_db()

    def _load_modules_db(self):
        """Загружает базу данных модулей из JSON-файла"""
        try:
            response = requests.get(self.modules_db_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error loading modules database: {str(e)}")
            return {}

    def search_modules(self, search_query):
        """Ищет модули по ключевым словам в JSON-базе"""
        search_query = search_query.lower()
        found_modules = {}
        
        for module_name, module_info in self.modules.items():
            # Ищем в названии модуля
            name_match = search_query in module_name.lower()
            
            # Ищем в описании
            desc_match = search_query in module_info.get('description', '').lower()
            
            # Ищем в ключевых словах
            keywords = [kw.lower() for kw in module_info.get('keywords', [])]
            kw_match = search_query in keywords
            
            # Ищем в командах
            commands = [cmd.lower() for cmd in module_info.get('commands', [])]
            cmd_match = search_query in commands
            
            if name_match or desc_match or kw_match or cmd_match:
                found_modules[module_name] = module_info
                
        return found_modules
        
class ModuleManager:
    def __init__(self, client):
        self.client = client
        self.modules = {}
        self.prefix = DEFAULT_PREFIX
        self.start_time = datetime.now()
        self.session_id = str(uuid.uuid4())[:8]
        self.version = self._get_version() or "1.0.0"
        self.last_update_time = self._get_last_update_time() or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os.makedirs(MODS_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._setup_logging()
        self.owner_id = None  # Добавлено для хранения ID владельца

    async def set_owner(self, owner_id):
        """Установка ID владельца"""
        self.owner_id = owner_id

    def _get_version(self):
        """Получаем версию бота"""
        try:
            # Сначала пробуем получить из git
            if os.path.exists('.git'):
                process = os.popen('git describe --tags --abbrev=0 2>/dev/null')
                version = process.read().strip()
                process.close()
                if version:
                    return version
            
            # Затем пробуем получить из файла
            if os.path.exists('version.txt'):
                with open('version.txt', 'r') as f:
                    return f.read().strip()
                    
            return None
        except:
            return None

    def _get_last_update_time(self):
        """Получаем дату последнего обновления"""
        try:
            if os.path.exists('.git'):
                process = os.popen('git log -1 --format=%cd --date=format:"%Y-%m-%d %H:%M:%S"')
                date = process.read().strip()
                process.close()
                return date
                
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except:
            return None

    def _setup_logging(self):
        """Настройка логирования"""
        import logging
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AcrokaUB')

    async def _backup_module(self, module_path: str):
        """Создание резервной копии модуля"""
        if not os.path.exists(module_path):
            return
            
        backup_dir = os.path.join(BACKUP_DIR, datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = os.path.join(backup_dir, os.path.basename(module_path))
        shutil.copy2(module_path, backup_path)
        self.logger.info(f"Created backup of {module_path} at {backup_path}")

    async def load_module(self, module_name: str) -> bool:
        try:
            self._clean_cache(module_name)
            module_path = os.path.join(MODS_DIR, f"{module_name}.py")
            
            await self._backup_module(module_path)
            
            if not await self._check_dependencies(module_path):
                return False
                
            spec = importlib.util.spec_from_file_location(
                f"userbot.mods.{module_name}", 
                module_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"userbot.mods.{module_name}"] = module
            spec.loader.exec_module(module)
            
            handlers = []
            if hasattr(module, 'on_load'):
                handlers = await module.on_load(self.client, self.prefix) or []
            
            self.modules[module_name] = {
                'module': module,
                'path': module_path,
                'handlers': handlers,
                'loaded_at': datetime.now(),
                'load_count': 1
            }
            
            print(f"✅ [Модуль] {module_name} успешно загружен")
            self.logger.info(f"Module {module_name} loaded successfully")
            return True
            
        except Exception as e:
            error_msg = f"Не удалось загрузить модуль {module_name}: {str(e)}"
            print(f"❌ [Ошибка] {error_msg}")
            self.logger.error(error_msg, exc_info=True)
            if os.path.exists(module_path):
                os.remove(module_path)
            return False
            
    async def _check_dependencies(self, module_path: str) -> bool:
        """Проверка и установка зависимостей модуля"""
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            requires = re.search(r'#\s*requires?:\s*(.+)', content)
            if not requires:
                return True
                
            dependencies = [dep.strip() for dep in requires.group(1).split(',')]
            print(f"🔍 [Зависимости] Установка для модуля: {', '.join(dependencies)}")
            self.logger.info(f"Installing dependencies: {', '.join(dependencies)}")
            
            process = await asyncio.create_subprocess_shell(
                f"{sys.executable} -m pip install --upgrade {' '.join(dependencies)}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = f"Не удалось установить зависимости:\n{stderr.decode()}"
                print(f"❌ [Ошибка] {error_msg}")
                self.logger.error(error_msg)
                return False
                
            print(f"✅ [Зависимости] Успешно установлены: {', '.join(dependencies)}")
            self.logger.info(f"Dependencies installed: {', '.join(dependencies)}")
            return True
            
        except Exception as e:
            error_msg = f"Проверка зависимостей: {str(e)}"
            print(f"❌ [Ошибка] {error_msg}")
            self.logger.error(error_msg, exc_info=True)
            return False

    async def reload_module(self, module_name: str) -> bool:
        if module_name not in self.modules:
            return await self.load_module(module_name)
            
        if not await self.unload_module(module_name):
            return False
            
        if await self.load_module(module_name):
            self.modules[module_name]['load_count'] += 1
            return True
        return False

    async def unload_module(self, module_name: str) -> bool:
        if module_name not in self.modules:
            return False
            
        module_data = self.modules[module_name]
        
        try:
            if hasattr(module_data['module'], 'on_unload'):
                await module_data['module'].on_unload()
            
            for handler in module_data['handlers']:
                self.client.remove_event_handler(handler)
            
            del sys.modules[f"userbot.mods.{module_name}"]
            del self.modules[module_name]
            
            self._clean_cache(module_name)
            
            print(f"✅ [Модуль] {module_name} выгружен")
            self.logger.info(f"Module {module_name} unloaded")
            return True
            
        except Exception as e:
            error_msg = f"Не удалось выгрузить модуль {module_name}: {str(e)}"
            print(f"❌ [Ошибка] {error_msg}")
            self.logger.error(error_msg, exc_info=True)
            return False

    def _clean_cache(self, module_name: str):
        """Очистка кэша модуля"""
        cache_dir = os.path.join(MODS_DIR, '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        for root, _, files in os.walk(MODS_DIR):
            for file in files:
                if file.startswith(module_name) and file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))

    async def load_all_modules(self):
        print(f"🔍 [Система] Загрузка модулей...")
        
        if not os.path.exists(LOADED_MODS_FILE):
            for filename in os.listdir(MODS_DIR):
                if filename.endswith('.py') and not filename.startswith('_'):
                    await self.load_module(filename[:-3])
        else:
            with open(LOADED_MODS_FILE, 'r') as f:
                for module_name in f.read().splitlines():
                    if module_name:
                        await self.load_module(module_name)
            os.remove(LOADED_MODS_FILE)
        
        print(f"📦 [Система] Загружено {len(self.modules)} модулей")

    async def save_loaded_modules(self):
        with open(LOADED_MODS_FILE, 'w') as f:
            f.write('\n'.join(self.modules.keys()))
            
    async def download_module(self, url: str) -> str:
        """Скачивание модуля по URL"""
        try:
            # Проверяем, что URL принадлежит официальному репозиторию
            if not url.startswith(RAW_MODS_URL):
                raise ValueError("Недопустимый URL модуля. Разрешены только модули из официального репозитория.")
                
            module_name = os.path.basename(url)
            module_path = os.path.join(MODS_DIR, module_name)
            
            response = requests.get(url)
            response.raise_for_status()
            
            with open(module_path, 'wb') as f:
                f.write(response.content)
                
            return module_path
        except Exception as e:
            self.logger.error(f"Error downloading module: {str(e)}")
            if os.path.exists(module_path):
                os.remove(module_path)
            raise


class CoreCommands:
    def __init__(self, manager):
        self.manager = manager
        self.repo_url = GITHUB_REPO
        self.docs_url = DOCS_URL
    
    async def initialize(self):
        me = await self.manager.client.get_me()
        await self.manager.set_owner(me.id)  # Используем новый метод для установки владельца
        print(f"🔐 [Система] Владелец ID: {me.id}")
        self.manager.logger.info(f"Bot started for user ID: {me.id}")

    async def is_owner(self, event: Message) -> bool:
        """Проверка, является ли отправитель владельцем бота"""
        if not hasattr(event, 'sender_id'):
            return False
            
        if event.sender_id == self.manager.owner_id:
            return True
            
        try:
            await event.delete()
        except:
            pass
        return False

    async def handle_setprefix(self, event: Message):
        """Установка нового префикса"""
        if not await self.is_owner(event):
            return
            
        new_prefix = event.pattern_match.group(1)
        if not new_prefix or len(new_prefix) > 3:
            await event.edit("❌ Укажите новый префикс (1-3 символа)")
            return
            
        self.manager.prefix = new_prefix
        with open(PREFIX_FILE, 'w') as f:
            f.write(new_prefix)
            
        await event.edit(f"✅ Префикс изменен на: <code>{new_prefix}</code>", parse_mode='html')
        await self.manager.save_loaded_modules()
        await self.restart_bot()

    async def handle_setinfo(self, event: Message):
        """Установка кастомного текста для .info"""
        if not await self.is_owner(event):
            return
            
        template = event.pattern_match.group(1)
        
        if not template:
            # Показать текущий шаблон
            try:
                with open(CUSTOM_INFO_FILE, 'r') as f:
                    current_template = json.load(f).get('template', DEFAULT_INFO_TEMPLATE)
            except:
                current_template = DEFAULT_INFO_TEMPLATE
                
            await event.edit(
                f"ℹ️ <b>Текущий шаблон .info:</b>\n\n"
                f"<code>{current_template}</code>\n\n"
                f"Доступные переменные: version, session_id, last_update_time, "
                f"owner_id, owner_name, uptime, modules_count, os_info, python_version, "
                f"telethon_version, cpu_usage, cpu_cores, ram_percent, ram_used, "
                f"ram_total, repo_url",
                parse_mode='html'
            )
            return
            
        try:
            data = {'template': template}
            with open(CUSTOM_INFO_FILE, 'w') as f:
                json.dump(data, f)
                
            await event.edit("✅ Шаблон .info успешно обновлен!")
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")

    async def handle_media_info(self, event: Message):
        """Команда для загрузки медиа с текстом"""
        if not await self.is_owner(event):
            return
            
        if not event.is_reply:
            await event.edit("❌ Ответьте на сообщение с медиа")
            return
            
        reply = await event.get_reply_message()
        if not (reply.photo or reply.video or reply.document):
            await event.edit("❌ Сообщение должно содержать фото, видео или документ")
            return
            
        caption = event.pattern_match.group(1)
        if not caption:
            caption = ""
            
        try:
            media = await reply.download_media(file='temp_download')
            
            # Получаем информацию о системе
            info_msg = await self._generate_info_message()
            
            # Отправляем медиа с текстом
            if reply.photo:
                await event.delete()
                await self.manager.client.send_file(
                    event.chat_id,
                    media,
                    caption=f"{caption}\n\n{info_msg}" if caption else info_msg,
                    parse_mode='html'
                )
            elif reply.video or reply.document:
                await event.delete()
                await self.manager.client.send_file(
                    event.chat_id,
                    media,
                    caption=f"{caption}\n\n{info_msg}" if caption else info_msg,
                    parse_mode='html',
                    supports_streaming=True
                )
                
            os.remove(media)
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")
            if os.path.exists(media):
                os.remove(media)

    async def _generate_info_message(self):
        """Генерация сообщения .info с учетом кастомного шаблона"""
        me = await self.manager.client.get_me()
        uptime = datetime.now() - self.manager.start_time
        sys_info = self.manager.get_system_info()
        
        try:
            with open(CUSTOM_INFO_FILE, 'r') as f:
                template = json.load(f).get('template', DEFAULT_INFO_TEMPLATE)
        except:
            template = DEFAULT_INFO_TEMPLATE
        
        info_data = {
            'version': self.manager.version,
            'session_id': self.manager.session_id,
            'last_update_time': self.manager.last_update_time,
            'owner_id': me.id,
            'owner_name': me.first_name,
            'uptime': str(timedelta(seconds=uptime.seconds)).split('.')[0],
            'modules_count': len(self.manager.modules),
            'os_info': f"{platform.system()} {platform.release()}",
            'python_version': platform.python_version(),
            'telethon_version': telethon.__version__,
            'cpu_usage': sys_info.get('cpu', {}).get('usage', 'N/A'),
            'cpu_cores': sys_info.get('cpu', {}).get('cores', 'N/A'),
            'ram_percent': sys_info.get('memory', {}).get('percent', 'N/A'),
            'ram_used': sys_info.get('memory', {}).get('used', 'N/A'),
            'ram_total': sys_info.get('memory', {}).get('total', 'N/A'),
            'repo_url': self.repo_url
        }
        
        return template.format(**info_data)    
                    
    async def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """Получение информации о модуле в структурированном виде"""
        if module_name not in self.manager.modules:
            return None
            
        module_data = self.manager.modules[module_name]
        module = module_data['module']
        
        # Получаем docstring и очищаем его
        docstring = (module.__doc__ or "Без описания").strip()
        description = "\n".join(line.strip() for line in docstring.split("\n"))
        
        # Получаем версию модуля
        version = getattr(module, 'version', '1.0')
        
        # Получаем команды модуля
        commands = getattr(module, 'commands', {})
        formatted_commands = []
        
        if isinstance(commands, dict):
            formatted_commands = [
                f"{self.manager.prefix}{cmd} - {desc}" 
                for cmd, desc in commands.items()
            ]
        elif isinstance(commands, (list, tuple)):
            formatted_commands = [f"{self.manager.prefix}{cmd}" for cmd in commands]
        
        return {
            'name': module_name,
            'description': description,
            'version': version,
            'commands': formatted_commands,
            'path': module_data['path'],
            'loaded_at': module_data['loaded_at'],
            'load_count': module_data.get('load_count', 1)
        }

    async def handle_help(self, event: Message) -> None:
        """Основное сообщение помощи"""
        if not await self.is_owner(event):
            return
            
        prefix = self.manager.prefix
        
        help_msg = [
            f"✨ <b>Acroka UserBot Help (v{self.manager.version})</b> ✨",
            f"🔹 <b>Префикс:</b> <code>{prefix}</code>",
            f"🔹 <b>Сессия:</b> <code>{self.manager.session_id}</code>",
            "",
            "⚙️ <b>Основные команды:</b>",
            f"• <code>{prefix}help</code> - Показать это сообщение",
            f"• <code>{prefix}ping</code> - Проверить работоспособность бота",
            f"• <code>{prefix}info</code> - Информация о боте и системе",
            f"• <code>{prefix}update</code> - Обновить бота",
            f"• <code>{prefix}restart</code> - Перезапустить бота",
            f"• <code>{prefix}logs</code> - Получить файл логов",
            f"• <code>{prefix}setprefix [новый префикс]</code> - Изменить префикс команд",
            f"• <code>{prefix}setinfo [шаблон]</code> - Настроить вывод .info",
            f"• <code>{prefix}mediainfo [текст]</code> - Отправить медиа с системной информацией",
            "",
            "📦 <b>Управление модулями:</b>",
            f"• <code>{prefix}lm</code> - Загрузить модуль из ответа на файл",
            f"• <code>{prefix}gm [name]</code> - Получить файл модуля",
            f"• <code>{prefix}ulm [name]</code> - Выгрузить и удалить модуль",
            f"• <code>{prefix}rlm [name]</code> - Перезагрузить модуль",
            f"• <code>{prefix}mlist</code> - Список загруженных модулей (с командами)",
            f"• <code>{prefix}mfind [query]</code> - Поиск модулей в репозитории",
            f"• <code>{prefix}dlm [name]</code> - Скачать модуль из репозитория",
            f"• <code>{prefix}mhelp [name]</code> - Помощь по конкретному модулю",
            "",
            "🛠️ <b>Утилиты:</b>",
            f"• <code>{prefix}tr [lang] [text]</code> - Переводчик текста",
            f"• <code>{prefix}calc [expr]</code> - Калькулятор выражений",
            f"• <code>{prefix}clean</code> - Очистка кэша и временных файлов",
            "",
            "🔗 <b>Ссылки:</b>",
            f"• <a href='{self.repo_url}'>Репозиторий</a>",
            f"• <a href='{self.docs_url}'>Документация</a>"
        ]
        
        await event.edit("\n".join(help_msg), parse_mode='html')
        
    async def handle_module_help(self, event: Message) -> None:
        """Детальная информация о модуле"""
        if not await self.is_owner(event):
            return
            
        module_name = event.pattern_match.group(1)
        if not module_name:
            await event.edit("❌ Укажите название модуля")
            return

        module_info = await self.get_module_info(module_name)
        if not module_info:
            await event.edit(f"❌ Модуль <code>{module_name}</code> не найден", parse_mode='html')
            return
            
        try:
            uptime = datetime.now() - module_info['loaded_at']
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            info_msg = [
                f"📦 <b>Модуль {module_info['name']} v{module_info['version']}</b>",
                "",
                f"📝 <b>Описание:</b> {module_info['description']}",
                ""
            ]
            
            if module_info['commands']:
                info_msg.append("⚙️ <b>Доступные команды:</b>")
                info_msg.extend([f"• <code>{cmd}</code>" for cmd in module_info['commands']])
                info_msg.append("")
            
            info_msg.extend([
                f"🕒 <b>Загружен:</b> {hours}ч {minutes}м назад",
                f"🔄 <b>Перезагрузок:</b> {module_info['load_count']}",
                f"📂 <b>Файл:</b> <code>{os.path.basename(module_info['path'])}</code>"
            ])
            
            await event.edit("\n".join(info_msg), parse_mode='html')
            
        except Exception as e:
            await event.edit(f"❌ Ошибка при получении информации о модуле: {str(e)}")

    async def handle_getmod(self, event: Message):
        """Отправить файл модуля в чат"""
        if not await self.is_owner(event):
            return
            
        module_name = event.pattern_match.group(1)
        
        if module_name not in self.manager.modules:
            await event.edit(
                "❌ <b>Модуль не найден</b>\n\n"
                f"Модуль <code>{module_name}</code> не загружен.",
                parse_mode='html'
            )
            return
            
        try:
            module_data = self.manager.modules[module_name]
            module = module_data['module']
            
            desc = getattr(module, 'doc', 'Без описания').strip()
            version = getattr(module, 'version', '1.0')
            commands = getattr(module, 'commands', [])
            
            info_msg = [
                f"📦 <b>Модуль {module_name} v{version}</b>",
                f"📝 <b>Описание:</b> {desc}",
                "",
                "🛠 <b>Команды:</b>",
                *[f"• <code>{self.manager.prefix}{cmd}</code>" for cmd in commands],
                "",
                "⬇️ <i>Файл модуля:</i>"
            ]
            
            await event.delete()
            await self.manager.client.send_message(
                event.chat_id,
                "\n".join(info_msg),
                parse_mode='html',
                file=module_data['path']
            )
            
        except Exception as e:
            await event.edit(
                "❌ <b>Ошибка получения модуля</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='html'
                           )    
    
    async def handle_logs(self, event: Message):
        """Отправка логов"""
        if not await self.is_owner(event):
            return
            
        try:
            if not os.path.exists(LOG_FILE):
                await event.edit("ℹ️ Файл логов не найден")
                return
                
            await event.delete()
            await self.manager.client.send_file(
                event.chat_id,
                LOG_FILE,
                caption=f"📄 Логи юзербота (Session ID: {self.manager.session_id})"
            )
        except Exception as e:
            await event.edit(f"❌ Ошибка при получении логов: {str(e)}")

    def get_system_info(self):
        """Получение информации о системе"""
        try:
            mem = psutil.virtual_memory()
            return {
                'memory': {
                    'used': round(mem.used / 1024 / 1024, 1),
                    'total': round(mem.total / 1024 / 1024, 1),
                    'percent': mem.percent
                },
                'cpu': {
                    'cores': psutil.cpu_count(),
                    'usage': psutil.cpu_percent()
                },
                'uptime': str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0]
            }
        except Exception as e:
            self.manager.logger.error(f"Error getting system info: {str(e)}")
            return {}

        async def handle_info(event):
            if not await self.is_owner(event):
                return
            await event.edit(await self._generate_info_message(), parse_mode='html', link_preview=False)
        
        cmd_handlers.append((rf'^{prefix}info$', handle_info))

        for pattern, handler in cmd_handlers:
            self.manager.client.add_event_handler(
                handler,
                events.NewMessage(pattern=pattern, outgoing=True)
            )
            
    async def is_owner(self, event):
        # Эта функция должна проверять является ли пользователь владельцем
        return event.sender_id == self.manager.owner_id  # Пример, как может быть реализовано        
    async def handle_reloadmod(self, event: Message):
        """Перезагрузка модуля"""
        if not await self.is_owner(event):
            return
            
        module_name = event.pattern_match.group(1)
        
        if not module_name:
            await event.edit("❌ Укажите имя модуля для перезагрузки")
            return
            
        try:
            if await self.manager.reload_module(module_name):
                await event.edit(f"✅ Модуль <code>{module_name}</code> успешно перезагружен!", parse_mode='html')
            else:
                await event.edit(f"❌ Не удалось перезагрузить модуль <code>{module_name}</code>", parse_mode='html')
        except Exception as e:
            await event.edit(f"❌ Ошибка при перезагрузке модуля: {str(e)}")

    async def handle_ping(self, event: Message):
        """Обработчик команды ping"""
        if not await self.is_owner(event):
            return
            
        start = datetime.now()
        msg = await event.edit("🏓 Pong!")
        latency = (datetime.now() - start).microseconds / 1000
        await msg.edit(f"🏓 Pong! | {latency}ms")

    async def handle_update(self, event: Message):
        """Обновление бота с сохранением папки source"""
        if not await self.is_owner(event):
            return

        try:
            msg = await event.edit("🔄 <b>Начало безопасного обновления...</b>", parse_mode='html')

            # 1. Создаем временную папку для обновления
            temp_dir = "temp_update"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            # 2. Клонируем репозиторий во временную папку
            await msg.edit("🔄 <b>Загрузка обновлений...</b>", parse_mode='html')
            clone_cmd = f"git clone {self.repo_url} {temp_dir}"
            process = await asyncio.create_subprocess_shell(
                clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if process.returncode != 0:
                shutil.rmtree(temp_dir)
                return await msg.edit("❌ <b>Ошибка при загрузке обновлений</b>", parse_mode='html')

            # 3. Копируем только нужные файлы, исключая папку source
            await msg.edit("🔄 <b>Применение обновлений...</b>", parse_mode='html')
            excluded = {'source', '.git', 'pycache', temp_dir}
            
            for item in os.listdir(temp_dir):
                if item not in excluded:
                    src_path = os.path.join(temp_dir, item)
                    dest_path = os.path.join('.', item)
                    
                    if os.path.exists(dest_path):
                        if os.path.isdir(dest_path):
                            shutil.rmtree(dest_path)
                        else:
                            os.remove(dest_path)
                    
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dest_path)
                    else:
                        shutil.copy2(src_path, dest_path)

            # 4. Получаем версию обновления
            version_file = os.path.join(temp_dir, 'version.txt')
            new_version = "unknown"
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    new_version = f.read().strip()

            # 5. Очистка временных файлов
            shutil.rmtree(temp_dir)

            # 6. Обновление зависимостей
            await msg.edit("🔄 <b>Обновление зависимостей...</b>", parse_mode='html')
            if os.path.exists('requirements.txt'):
                process = await asyncio.create_subprocess_shell(
                    f"{sys.executable} -m pip install -r requirements.txt --upgrade",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

            await msg.edit(
                f"🎉 <b>Бот успешно обновлен!</b>\n\n"
                f"<b>Новая версия:</b> <code>{new_version}</code>\n\n"
                "✅ <b>Папка source сохранена</b>\n"
                "🔄 <b>Перезапуск через 5 секунд...</b>",
                parse_mode='html'
            )

            await asyncio.sleep(5)
            await self.restart_bot()

        except Exception as e:
            error_msg = (
                f"❌ <b>Ошибка обновления</b>\n\n"
                f"<code>{str(e)}</code>\n\n"
                "Попробуйте вручную:\n"
                "1. Скачайте архив с GitHub\n"
                "2. Скопируйте файлы, кроме папки source\n"
                "3. Перезапустите бота"
            )
            await event.edit(error_msg, parse_mode='html')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    
    async def handle_clean(self, event: Message):
        """Очистка кэша и временных файлов"""
        if not await self.is_owner(event):
            return
            
        try:
            msg = await event.edit("🧹 <b>Очистка кэша...</b>", parse_mode='html')
            
            for root, _, files in os.walk('.'):
                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        os.remove(os.path.join(root, file))
            
            for root, dirs, _ in os.walk('.'):
                if '__pycache__' in dirs:
                    shutil.rmtree(os.path.join(root, '__pycache__'))
            
            await msg.edit(
                "✅ <b>Очистка завершена!</b>\n\n"
                "Все временные файлы и кэш удалены.",
                parse_mode='html'
            )
            
        except Exception as e:
            await event.edit(
                "❌ <b>Ошибка очистки</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='html'
            )

    async def handle_loadmod(self, event: Message):
        """Загрузка модуля"""
        if not await self.is_owner(event):
            return
            
        if not event.is_reply:
            response = await event.edit("❌ Ответьте на файл модуля (.py)")
            await asyncio.sleep(3)
            await response.delete()
            return
            
        reply = await event.get_reply_message()
        if not reply.file or not reply.file.name.endswith('.py'):
            response = await event.edit("❌ Файл должен быть .py модулем")
            await asyncio.sleep(3)
            await response.delete()
            return
            
        try:
            path = await reply.download_media(file=MODS_DIR)
            module_name = os.path.splitext(os.path.basename(path))[0]
            
            if await self.manager.load_module(module_name):
                module_data = self.manager.modules[module_name]
                module = module_data['module']
                
                desc = getattr(module, '__doc__', 'Без описания').strip()
                version = getattr(module, 'version', '1.0')
                commands = getattr(module, 'commands', {})
                
                desc = desc.replace("Описание:", "").strip()
                
                formatted_commands = []
                if isinstance(commands, dict):
                    for cmd, cmd_desc in commands.items():
                        if cmd_desc:
                            formatted_commands.append(f"• <code>{self.manager.prefix}{cmd}</code> - {cmd_desc}")
                        else:
                            formatted_commands.append(f"• <code>{self.manager.prefix}{cmd}</code>")
                elif isinstance(commands, list):
                    formatted_commands = [f"• <code>{self.manager.prefix}{cmd}</code>" for cmd in commands]
                
                info_msg = [
                    f"✅ <b>Модуль {module_name} v{version} успешно загружен!</b>",
                    "",
                    f"📝 <b>Описание:</b> {desc}",
                    ""
                ]
                
                if formatted_commands:
                    info_msg.extend([
                        "⚙️ <b>Доступные команды:</b>",
                        *formatted_commands,
                        ""
                    ])
                
                await event.edit("\n".join(info_msg), parse_mode='html')
            else:
                await event.edit("❌ Ошибка загрузки модуля")
                
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")
            if os.path.exists(path):
                os.remove(path)

    async def handle_searchmod(self, event: Message):
        if not await self.is_owner(event):
            return
            
        search_query = event.pattern_match.group(1)
        if not search_query:
            await event.edit("❌ Укажите поисковый запрос")
            return
            
        try:
            await event.edit("🔍 Поиск модулей...")
            finder = ModuleFinder(MODS_REPO)
            found_modules = finder.search_modules(search_query)

            if not found_modules:
                await event.edit(f"🔍 По запросу '{search_query}' ничего не найдено")
                return

            results = []
            for module_name, info in found_modules.items():
                keywords = ", ".join(info['keywords']) if info['keywords'] else "нет"
                results.append(
                    f"📦 <b>{module_name}</b> (v{info['version']})\n"
                    f"📝 <i>{info['description'][:100]}</i>\n"
                    f"🔎 <b>Ключевые слова:</b> {keywords}\n"
                    f"⬇️ <code>{self.manager.prefix}dlm {module_name}.py</code>\n"
                )

            message = [
                f"🔍 <b>Результаты поиска по запросу '{search_query}':</b>",
                f"📂 Найдено модулей: {len(found_modules)}",
                "",
                *results,
                ""
            ]
            
            await event.edit("\n".join(message), parse_mode='html')

        except Exception as e:
            await event.edit(f"❌ Ошибка поиска: {str(e)}")
            
    async def handle_downloadmod(self, event: Message):
        if not await self.is_owner(event):
            return
            
        module_file = event.pattern_match.group(1)
        if not module_file:
            await event.edit("❌ Укажите имя файла модуля (например: .dlm example.py)")
            return
            
        if not module_file.endswith('.py'):
            module_file += '.py'
            
        try:

            msg = await event.edit(f"⬇️ Скачивание модуля {module_file}...")
            
            module_url = f"{RAW_MODS_URL}{module_file}"
            module_path = await self.manager.download_module(module_url)
            
            module_name = os.path.splitext(module_file)[0]
            if await self.manager.load_module(module_name):
                await msg.edit(
                    f"✅ <b>Модуль {module_name} успешно установлен!</b>\n\n"
                    f"Файл: <code>{module_file}</code>\n"
                    f"Источник: <code>{MODS_REPO}</code>\n\n"
                    f"Для информации о модуле используйте <code>{self.manager.prefix}gm {module_name}</code>",
                    parse_mode='html'
                )
            else:
                await msg.edit(
                    "⚠️ <b>Модуль скачан, но не загружен</b>\n\n"
                    f"Файл: <code>{module_file}</code>\n"
                    f"Проверьте логи для подробностей: <code>{self.manager.prefix}logs</code>",
                    parse_mode='html'
                )
                
        except ValueError as e:
            await event.edit(
                "❌ <b>Ошибка безопасности</b>\n\n"
                f"{str(e)}\n\n"
                "Разрешены только модули из официального репозитория: "
                f"<code>{MODS_REPO}</code>",
                parse_mode='html'
            )
        except Exception as e:
            await event.edit(
                "❌ <b>Ошибка загрузки модуля</b>\n\n"
                f"<code>{str(e)}</code>\n\n"
                "Проверьте:\n"
                "1. Правильность имени модуля\n"
                "2. Наличие модуля в репозитории\n"
                f"3. Доступность репозитория: <code>{MODS_REPO}</code>",
                parse_mode='html'
            )
            if os.path.exists(module_path):
                os.remove(module_path)


    async def handle_unloadmod(self, event: Message):
        """Полностью удалить модуль"""
        if not await self.is_owner(event):
            return
            
        module_name = event.pattern_match.group(1)
        
        if module_name not in self.manager.modules:
            await event.edit(
                "❌ <b>Модуль не найден</b>\n\n"
                f"Модуль <code>{module_name}</code> не загружен.",
                parse_mode='html'
            )
            return
            
        try:
            module_path = self.manager.modules[module_name]['path']
            
            if await self.manager.unload_module(module_name):
                os.remove(module_path)
                await event.edit(
                    "✅ <b>Модуль полностью удален</b>\n\n"
                    f"Модуль <code>{module_name}</code> был:\n"
                    "1. Выгружен из памяти\n"
                    "2. Очищен кэш\n"
                    f"3. Файл удален: <code>{os.path.basename(module_path)}</code>",
                    parse_mode='html'
                )
            else:
                await event.edit(
                    "⚠️ <b>Не удалось выгрузить модуль</b>\n\n"
                    "Файл не был удален.",
                    parse_mode='html'
                )
                
        except Exception as e:
            await event.edit(
                "❌ <b>Ошибка удаления</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='html'
            )

    async def handle_modlist(self, event: Message):
        """Показать красивый список всех модулей с командами"""
        if not await self.is_owner(event):
            return
            
        if not self.manager.modules:
            await event.edit("ℹ️ Нет загруженных модулей")
            return
            
        mod_list = [
            f"📦 <b>Загруженные модули ({len(self.manager.modules)})</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        
        for mod_name, mod_data in self.manager.modules.items():
            module = mod_data['module']
            desc = (getattr(module, '__doc__', 'Без описания') or 'Без описания').split('\n')[0].strip()
            version = getattr(module, 'version', '1.0')
            uptime = datetime.now() - mod_data['loaded_at']
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            # Получаем команды модуля
            commands = getattr(module, 'commands', {})
            formatted_commands = []
            
            if isinstance(commands, dict):
                formatted_commands = [f"{self.manager.prefix}{cmd}" for cmd in commands.keys()]
            elif isinstance(commands, (list, tuple)):
                formatted_commands = [f"{self.manager.prefix}{cmd}" for cmd in commands]
            
            mod_list.extend([
                f"🔹 <b>{mod_name}</b> v{version}",
                f"   ├ <i>{desc}</i>",
                f"   ├ 🕒 Загружен: {hours}ч {minutes}м назад",
                f"   ├ 📂 <code>{os.path.basename(mod_data['path'])}</code>",
                f"   └ ⚙️ <b>Команды:</b> {', '.join(formatted_commands) if formatted_commands else 'нет'}",
                ""
            ])
        
        mod_list.append("🚀 Используйте <code>.mhelp [имя]</code> для подробной информации")
        
        full_message = "\n".join(mod_list)
        if len(full_message) > 4096:
            parts = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
            for part in parts:
                await event.respond(part, parse_mode='html')
                await asyncio.sleep(0.5)
            await event.delete()
        else:
            await event.edit(full_message, parse_mode='html')
            
    async def handle_translate(self, event: Message):
        """Переводчик"""
        if not await self.is_owner(event):
            return
            
        if not event.is_reply:
            await event.edit("❌ Ответьте на сообщение для перевода")
            return
            
        target_lang = event.pattern_match.group(1)
        if not target_lang:
            await event.edit("❌ Укажите язык перевода (например: .tr en)")
            return
            
        reply = await event.get_reply_message()
        text = reply.text
        
        try:
            translator = Translator()
            translated = translator.translate(text, dest=target_lang)
            await event.edit(
                f"🌐 Перевод ({translated.src} → {target_lang}):\n\n"
                f"{translated.text}"
            )
        except Exception as e:
            await event.edit(f"❌ Ошибка перевода: {str(e)}")

    async def handle_calc(self, event: Message):
        """Калькулятор"""
        if not await self.is_owner(event):
            return
            
        expr = event.pattern_match.group(1)
        try:
            result = eval(expr)
            await event.edit(f"🧮 Результат: {result}")
        except Exception as e:
            await event.edit(f"❌ Ошибка вычисления: {str(e)}")

    async def restart_bot(self, event: Message = None):
        """Перезагрузка юзербота"""
        if event and not await self.is_owner(event):
            return
            
        if event:
            await event.edit("🔄 Перезагрузка...")
        
        await self.manager.save_loaded_modules()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def register_handlers(self):
        prefix = re.escape(self.manager.prefix)
        
        cmd_handlers = [
            (rf'^{prefix}help$', self.handle_help),
            (rf'^{prefix}ping$', self.handle_ping),
            (rf'^{prefix}info$', self.handle_info),
            (rf'^{prefix}update$', self.handle_update),
            (rf'^{prefix}clean$', self.handle_clean),
            (rf'^{prefix}lm$', self.handle_loadmod),
            (rf'^{prefix}gm (\w+)$', self.handle_getmod),
            (rf'^{prefix}ulm (\w+)$', self.handle_unloadmod),
            (rf'^{prefix}rlm (\w+)$', self.handle_reloadmod),
            (rf'^{prefix}mlist$', self.handle_modlist),
            (rf'^{prefix}tr (\w+)$', self.handle_translate),
            (rf'^{prefix}calc (.+)$', self.handle_calc),
            (rf'^{prefix}restart$', self.restart_bot),
            (rf'^{prefix}logs$', self.handle_logs),
            (rf'^{prefix}mhelp (\w+)$', self.handle_module_help),
            (rf'^{prefix}mfind (.+)$', self.handle_searchmod),
            (rf'^{prefix}dlm (\w+\.py)$', self.handle_downloadmod),
            (rf'^{prefix}dlm (\w+)$', self.handle_downloadmod),
        ]
        
        for pattern, handler in cmd_handlers:
            self.manager.client.add_event_handler(
                handler,
                events.NewMessage(pattern=pattern, outgoing=True)
            )

import os
import subprocess
import platform

async def check_internet_connection() -> bool:
    """Проверка наличия интернет-соединения."""
    try:
        # Определяем операционную систему
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        # Выполняем команду ping на Google DNS
        output = subprocess.check_output(['ping', param, '1', '8.8.8.8'], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

async def main(client=None):
    """Основная функция запуска юзербота"""
    print("🟢 [Система] Запуск Acroka UserBot...")
    
    try:
        # Инициализация клиента
        if client is None:
            client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
            await client.start()
        
        print("✅ [Система] Юзербот авторизован")

        # Загрузка префикса
        prefix = DEFAULT_PREFIX
        if os.path.exists(PREFIX_FILE):
            with open(PREFIX_FILE, 'r') as f:
                prefix = f.read().strip() or DEFAULT_PREFIX

        # Инициализация менеджера модулей
        manager = ModuleManager(client)
        manager.prefix = prefix
        
        # Инициализация основных команд
        core_commands = CoreCommands(manager)
        await core_commands.initialize()
        core_commands.register_handlers()

        # Загрузка всех модулей
        await manager.load_all_modules()

        print(f"🟢 [Система] Юзербот запущен | Префикс: '{prefix}' | Версия: {manager.version}")
        print("🔹 Отправьте .help для списка команд")
        
        # Убедимся, что обработчики зарегистрированы
        print(f"🔹 Зарегистрировано обработчиков: {len(client.list_event_handlers())}")
        
        # Основной цикл
        await client.run_until_disconnected()
        
    except Exception as e:
        print(f"❌ [Критическая ошибка] {str(e)}")
        traceback.print_exc()
    finally:
        if 'client' in locals() and client.is_connected():
            await client.disconnect()
            print("🔴 [Система] Юзербот остановлен")

if __name__ == '__main__':
    # Убедимся, что используется правильный цикл событий
    if sys.platform == 'win32':
        asyncio.set_event_loop(asyncio.ProactorEventLoop())
    
    asyncio.run(main())
