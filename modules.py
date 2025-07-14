import os
import sys
import importlib
import asyncio
import re
import shutil
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
BACKUP_DIR = 'source/backups/'
LOG_FILE = 'userbot.log'

class ModuleManager:
    def __init__(self, client):
        self.client = client
        self.modules = {}
        self.prefix = DEFAULT_PREFIX
        self.start_time = datetime.now()
        self.session_id = str(uuid.uuid4())[:8]  # Уникальный ID сессии
        os.makedirs(MODS_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._setup_logging()

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
            
            # Создаем резервную копию перед загрузкой
            await self._backup_module(module_path)
            
            # Проверка зависимостей перед загрузкой
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
        """Перезагрузка модуля"""
        if module_name not in self.modules:
            return await self.load_module(module_name)
            
        if not await self.unload_module(module_name):
            return False
            
        # Обновляем счетчик загрузок
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
            
            # Полная очистка кэша
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
        """Полная очистка кэша модуля"""
        cache_dir = os.path.join(MODS_DIR, '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        # Удаление всех .pyc файлов для этого модуля
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

class CoreCommands:
    def __init__(self, manager):
        self.manager = manager
        self.owner_id = None
        self.repo_url = GITHUB_REPO
        self.host_info = self._get_host_info()
    
    def _get_host_info(self):
        """Получение информации о хосте"""
        try:
            return {
                'hostname': socket.gethostname(),
                'ip': socket.gethostbyname(socket.gethostname()),
                'platform': platform.platform()
            }
        except:
            return None

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

    def get_system_info(self):
        """Получение полной информации о системе"""
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            return {
                'memory': {
                    'total': round(mem.total / 1024 / 1024, 2),
                    'used': round(mem.used / 1024 / 1024, 2),
                    'free': round(mem.free / 1024 / 1024, 2),
                    'percent': mem.percent
                },
                'disk': {
                    'total': round(disk.total / 1024 / 1024),
                    'used': round(disk.used / 1024 / 1024),
                    'free': round(disk.free / 1024 / 1024),
                    'percent': disk.percent
                },
                'cpu': {
                    'cores': psutil.cpu_count(),
                    'usage': psutil.cpu_percent(),
                    'freq': psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else "N/A"
                },
                'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S'),
                'uptime': str(datetime.now() - boot_time).split('.')[0]
            }
        except Exception as e:
            self.manager.logger.error(f"Error getting system info: {str(e)}")
            return None

    async def handle_help(self, event: Message):
        if not await self.is_owner(event):
            return
            
        prefix = self.manager.prefix
        
        help_msg = [
            f"✨ <b>Acroka UserBot Help (Session ID: {self.manager.session_id})</b> ✨",
            "",
            "⚙️ <b>Основные команды:</b>",
            f"• <code>{prefix}help</code> - Показать это сообщение",
            f"• <code>{prefix}ping</code> - Проверка пинга",
            f"• <code>{prefix}info</code> - Информация о боте",
            f"• <code>{prefix}update</code> - Обновить бота",
            f"• <code>{prefix}restart</code> - Перезапустить бота",
            "",
            "📦 <b>Управление модулями:</b>",
            f"• <code>{prefix}loadmod</code> - Загрузить модуль",
            f"• <code>{prefix}getmod [name]</code> - Получить модуль",
            f"• <code>{prefix}unloadmod [name]</code> - Удалить модуль",
            f"• <code>{prefix}reloadmod [name]</code> - Перезагрузить модуль",
            f"• <code>{prefix}modlist</code> - Список модулей",
            "",
            "🛠️ <b>Утилиты:</b>",
            f"• <code>{prefix}tr [lang]</code> - Переводчик",
            f"• <code>{prefix}calc [expr]</code> - Калькулятор",
            f"• <code>{prefix}clean</code> - Очистка кэша",
            f"• <code>{prefix}logs</code> - Получить логи"
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

    async def handle_info(self, event: Message):
        if not await self.is_owner(event):
            return
            
        me = await self.manager.client.get_me()
        uptime = datetime.now() - self.manager.start_time
        sys_info = self.get_system_info()
        
        # Базовая информация
        info_msg = [
            f"🤖 <b>Acroka UserBot Info (Session ID: {self.manager.session_id})</b>",
            "",
            f"👤 <b>Владелец:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>",
            f"🆔 <b>ID:</b> <code>{me.id}</code>",
            f"⏱ <b>Аптайм:</b> {str(timedelta(seconds=uptime.seconds)).split('.')[0]}",
            f"📦 <b>Модулей:</b> {len(self.manager.modules)}",
            f"🔹 <b>Префикс:</b> <code>{self.manager.prefix}</code>",
            ""
        ]
        
        # Информация о системе
        if sys_info:
            info_msg.extend([
                "⚙️ <b>Системная информация:</b>",
                f"• <b>ОС:</b> {platform.system()} {platform.release()}",
                f"• <b>Python:</b> {platform.python_version()}",
                f"• <b>Telethon:</b> {telethon.__version__}",
                "",
                "💾 <b>Память:</b>",
                f"• <b>Использовано:</b> {sys_info['memory']['used']} MB / {sys_info['memory']['total']} MB ({sys_info['memory']['percent']}%)",
                "",
                "🖥 <b>Процессор:</b>",
                f"• <b>Ядер:</b> {sys_info['cpu']['cores']}",
                f"• <b>Нагрузка:</b> {sys_info['cpu']['usage']}%",
                f"• <b>Частота:</b> {sys_info['cpu']['freq']} MHz" if isinstance(sys_info['cpu']['freq'], (int, float)) else "",
                "",
                "💽 <b>Диск:</b>",
                f"• <b>Использовано:</b> {sys_info['disk']['used']} MB / {sys_info['disk']['total']} MB ({sys_info['disk']['percent']}%)",
                "",
                f"⏳ <b>Время работы системы:</b> {sys_info['uptime']}",
                f"🔌 <b>Последняя перезагрузка:</b> {sys_info['boot_time']}",
                ""
            ])
        
        # Информация о хосте
        if self.host_info:
            info_msg.extend([
                "🖥 <b>Хост:</b>",
                f"• <b>Имя:</b> {self.host_info['hostname']}",
                f"• <b>IP:</b> {self.host_info['ip']}",
                f"• <b>Платформа:</b> {self.host_info['platform']}",
                ""
            ])
        
        # Информация о модулях
        if self.manager.modules:
            info_msg.append("📊 <b>Статистика модулей:</b>")
            for mod_name, mod_data in self.manager.modules.items():
                uptime = datetime.now() - mod_data['loaded_at']
                info_msg.append(
                    f"• <b>{mod_name}</b> - загружен {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м назад "
                    f"(загрузок: {mod_data.get('load_count', 1)})"
                )
            info_msg.append("")
        
        info_msg.append(f"🔗 <b>Репозиторий:</b> <code>{self.repo_url}</code>")

        await event.edit("\n".join([line for line in info_msg if line]), parse_mode='html', link_preview=False)

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
        """Обновление бота из GitHub"""
        if not await self.is_owner(event):
            return
            
        try:
            msg = await event.edit("🔄 <b>Проверка обновлений...</b>", parse_mode='html')
            
            if not os.path.exists('.git'):
                return await msg.edit("❌ Это не git-репозиторий!", parse_mode='html')
            
            process = await asyncio.create_subprocess_shell(
                'git describe --tags',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            current_version = stdout.decode().strip()
            
            await msg.edit(
                f"🔍 <b>Текущая версия:</b> <code>{current_version}</code>\n"
                "🔄 <b>Проверяем обновления...</b>",
                parse_mode='html'
            )
            
            commands = [
                'git fetch --all',
                'git reset --hard origin/main',
                'git pull origin main'
            ]
            
            for cmd in commands:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            process = await asyncio.create_subprocess_shell(
                'git describe --tags',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            new_version = stdout.decode().strip()
            
            if current_version == new_version:
                return await msg.edit(
                    "✅ <b>У вас уже последняя версия!</b>\n"
                    f"<b>Версия:</b> <code>{current_version}</code>",
                    parse_mode='html'
                )
            
            await msg.edit(
                f"🎉 <b>Бот успешно обновлен!</b>\n\n"
                f"<b>Было:</b> <code>{current_version}</code>\n"
                f"<b>Стало:</b> <code>{new_version}</code>\n\n"
                "🔄 <b>Перезапуск через 5 секунд...</b>",
                parse_mode='html'
            )
            
            await asyncio.sleep(5)
            await self.restart_bot()
            
        except Exception as e:
            await event.edit(
                "❌ <b>Ошибка обновления</b>\n\n"
                f"<code>{str(e)}</code>",
                parse_mode='html'
            )

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
            path = await reply.download_media(file=self.MODS_DIR)
            module_name = os.path.splitext(os.path.basename(path))[0]
            
            if await self.manager.load_module(module_name):
                # Получаем информацию о модуле
                module_data = self.manager.modules[module_name]
                module = module_data['module']
                
                # Получаем описание из docstring
                desc = (getattr(module, '__doc__', 'Без описания').strip().split('\n')[0].strip())
                
                # Получаем версию 
                version = getattr(module, 'version', '1.0')
                
                # Получаем команды
                commands = getattr(module, 'commands', {})
                if isinstance(commands, list):
                    # Преобразуем список команд в словарь с пустыми описаниями
                    commands = {cmd: "" for cmd in commands}
                
                # Формируем информационное сообщение
                info_msg = [
                    f"✅ <b>Модуль {module_name} v{version} успешно загружен!</b>",
                    "",
                    f"📝 <b>Описание:</b> {desc}",
                    ""
                ]
                
                if commands:
                    info_msg.append("⚙️ <b>Доступные команды:</b>")
                    for cmd, desc in commands.items():
                        cmd_desc = f" - {desc}" if desc else ""
                        info_msg.append(f"• <code>{self.manager.prefix}{cmd}</code>{cmd_desc}")
                    info_msg.append("")
                
                await event.edit("\n".join(info_msg), parse_mode='html')
            else:
                await event.edit("❌ Ошибка загрузки модуля")
                
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")
            if os.path.exists(path):
                os.remove(path)

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
            (rf'^{prefix}loadmod$', self.handle_loadmod),
            (rf'^{prefix}getmod (\w+)$', self.handle_getmod),
            (rf'^{prefix}unloadmod (\w+)$', self.handle_unloadmod),
            (rf'^{prefix}reloadmod (\w+)$', self.handle_reloadmod),
            (rf'^{prefix}modlist$', self.handle_modlist),
            (rf'^{prefix}tr (\w+)$', self.handle_translate),
            (rf'^{prefix}calc (.+)$', self.handle_calc),
            (rf'^{prefix}restart$', self.restart_bot),
            (rf'^{prefix}logs$', self.handle_logs),
        ]
        
        for pattern, handler in cmd_handlers:
            self.manager.client.add_event_handler(
                handler,
                events.NewMessage(pattern=pattern, outgoing=True)
            )

async def main(client=None):
    if client is None:
        client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
        try:
            await client.start()
            print("✅ [Система] Юзербот авторизован")
        except Exception as e:
            print(f"❌ [Ошибка авторизации] {str(e)}")
            return
    
    try:
        prefix = DEFAULT_PREFIX
        if os.path.exists(PREFIX_FILE):
            with open(PREFIX_FILE, 'r') as f:
                prefix = f.read().strip() or DEFAULT_PREFIX

        manager = ModuleManager(client)
        manager.prefix = prefix
        
        core_commands = CoreCommands(manager)
        await core_commands.initialize()
        core_commands.register_handlers()

        await manager.load_all_modules()

        print(f"🟢 [Система] Юзербот запущен | Префикс: '{prefix}'")
        print("🔹 Отправьте .help для списка команд")
        
        await client.run_until_disconnected()
        
    except Exception as e:
        print(f"❌ [Ошибка] {str(e)}")
        traceback.print_exc()
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())