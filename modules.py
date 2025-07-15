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

class ModuleFinder:
    def __init__(self, repo_url):
        self.repo_url = repo_url
        self.modules = self._load_modules()

    def _load_modules(self):
        """Загрузить список всех модулей из репозитория."""
        try:
            response = requests.get(f"{self.repo_url}/main/")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', class_='js-navigation-open link-gray')

            modules = {}
            for link in links:
                if link.get_text().endswith('.py'):
                    module_name = link.get_text()[:-3]
                    modules[module_name] = self._load_module_info(module_name)
            
            return modules
        except Exception as e:
            print(f"Error loading modules: {str(e)}")
            return {}

    def _load_module_info(self, module_name):
        """Загружает информацию о модуле."""
        try:
            url = f"{RAW_MODS_URL}{module_name}.py"
            response = requests.get(url)
            response.raise_for_status()
            
            content = response.text
            info = {
                'description': "Без описания",
                'version': "1.0",
                'keywords': []
            }
            
            # Поиск docstring
            doc_match = re.search(r'\"\"\"(.*?)\"\"\"', content, re.DOTALL)
            if doc_match:
                info['description'] = doc_match.group(1).strip().split('\n')[0]
                
            # Поиск ключевых слов
            kw_match = re.search(r'#\s*keywords?:\s*(.+)', content)
            if kw_match:
                info['keywords'] = [kw.strip().lower() for kw in kw_match.group(1).split(',')]
                
            # Поиск версии
            ver_match = re.search(r'#\s*version:\s*([\d.]+)', content)
            if ver_match:
                info['version'] = ver_match.group(1)
                
            return info
        except Exception:
            return {
                'description': "Ошибка загрузки информации",
                'version': "1.0",
                'keywords': []
            }

    def search_modules(self, search_query):
        """Ищет модули по ключевым словам."""
        search_query = search_query.lower()
        found_modules = {}
        
        for name, info in self.modules.items():
            if (search_query in name.lower() or 
                any(search_query in kw for kw in info['keywords']) or 
                search_query in info['description'].lower()):
                found_modules[name] = info
                
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
        self.owner_id = None
        self.repo_url = GITHUB_REPO
        self.docs_url = DOCS_URL
    
    async def initialize(self):
        me = await self.manager.client.get_me()
        self.owner_id = me.id
        print(f"🔐 [Система] Владелец ID: {self.owner_id}")
        self.manager.logger.info(f"Bot started for user ID: {self.owner_id}")

    async def is_owner(self, event: Message) -> bool:
        if event.sender_id == self.owner_id:
            return True
        try:
            await event.delete()
        except:
            pass
        return False

    async def handle_help(self, event: Message):
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
            f"• <code>{prefix}ping</code> - Проверка пинга",
            f"• <code>{prefix}info</code> - Информация о боте",
            f"• <code>{prefix}update</code> - Обновить бота",
            f"• <code>{prefix}restart</code> - Перезапустить бота",
            f"• <code>{prefix}logs</code> - Получить логи",
            "",
            "📦 <b>Управление модулями:</b>",
            f"• <code>{prefix}lm</code> - Загрузить модуль (ответом на файл)",
            f"• <code>{prefix}gm [name]</code> - Получить модуль",
            f"• <code>{prefix}ulm [name]</code> - Удалить модуль",
            f"• <code>{prefix}rlm [name]</code> - Перезагрузить модуль",
            f"• <code>{prefix}mlist</code> - Список модулей",
            f"• <code>{prefix}mfind [query]</code> - Поиск модулей",
            f"• <code>{prefix}dlm [name]</code> - Скачать модуль",
            "",
            "🛠️ <b>Утилиты:</b>",
            f"• <code>{prefix}tr [lang] [text]</code> - Переводчик",
            f"• <code>{prefix}calc [expr]</code> - Калькулятор",
            f"• <code>{prefix}clean</code> - Очистка кэша",
            "",
            "🔗 <b>Ссылки:</b>",
            f"• <a href='{self.repo_url}'>Репозиторий</a>",
            f"• <a href='{self.docs_url}'>Документация</a>"
        ]
        
        if self.manager.modules:
            help_msg.extend(["", "🔌 <b>Загруженные модули:</b>"])
            for mod_name in self.manager.modules.keys():
                help_msg.append(f"• <code>{mod_name}</code>")

        await event.edit("\n".join(help_msg), parse_mode='html')
        
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

    async def handle_info(self, event):
        if not await self.is_owner(event):
            return

        me = await self.manager.client.get_me()
        uptime = datetime.now() - self.manager.start_time
        sys_info = self.get_system_info()

        info_msg = [
            f"🤖 <b>Acroka UserBot v{self.manager.version}</b>",
            f"🔹 <b>Сессия:</b> <code>{self.manager.session_id}</code>",
            f"🔹 <b>Обновлено:</b> <code>{self.manager.last_update_time}</code>",
            "",
            f"👤 <b>Владелец:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>",
            f"🆔 <b>ID:</b> <code>{me.id}</code>",
            f"⏱ <b>Аптайм:</b> {str(timedelta(seconds=uptime.seconds)).split('.')[0]}",
            f"📦 <b>Модулей:</b> {len(self.manager.modules)}",
            "",
            "⚙️ <b>Система:</b>",
            f"• <b>ОС:</b> {platform.system()} {platform.release()}",
            f"• <b>Python:</b> {platform.python_version()}",
            f"• <b>Telethon:</b> {telethon.__version__}",
        ]

        # Добавляем информацию о системе, если она доступна
        if sys_info:
            info_msg.extend([
                "",
                "💻 <b>Ресурсы:</b>",
                f"• <b>CPU:</b> {sys_info.get('cpu', {}).get('usage', 'N/A')}% "
                f"({sys_info.get('cpu', {}).get('cores', 'N/A')} ядер)",
                f"• <b>RAM:</b> {sys_info.get('memory', {}).get('percent', 'N/A')}% "
                f"({sys_info.get('memory', {}).get('used', 'N/A')}/"
                f"{sys_info.get('memory', {}).get('total', 'N/A')} MB)",
            ])

        info_msg.extend([
            "",
            f"📂 <b>Репозиторий:</b> <code>{self.repo_url}</code>"
        ])

        await event.edit("\n".join(info_msg), parse_mode='html', link_preview=False)

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
                "",
                f"ℹ️ Для установки используйте команду <code>{self.manager.prefix}dlm имя_модуля.py</code>"
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
            
            desc = getattr(module, '__doc__', 'Без описания').strip()
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
        """Показать список всех модулей"""
        if not await self.is_owner(event):
            return
            
        if not self.manager.modules:
            await event.edit("ℹ️ Нет загруженных модулей")
            return
            
        mod_list = [
            "📦 <b>Загруженные модули:</b>",
            f"🔹 Всего: {len(self.manager.modules)}",
            ""
        ]
        
        for mod_name, mod_data in self.manager.modules.items():
            module = mod_data['module']
            desc = getattr(module, '__doc__', 'Без описания').split('\n')[0]
            version = getattr(module, 'version', '1.0')
            uptime = datetime.now() - mod_data['loaded_at']
            
            mod_list.append(
                f"• <b>{mod_name}</b> (v{version})\n"
                f"  <i>{desc}</i>\n"
                f"  🕒 Загружен: {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м назад\n"
                f"  📂 <code>{os.path.basename(mod_data['path'])}</code>"
            )
        
        await event.edit("\n".join(mod_list), parse_mode='html')

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
    asyncio.run(main())

