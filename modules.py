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
DOCS_URL = "https://github.com/theLuni/AcrokaUB/wiki"
BACKUP_DIR = 'source/backups/'
LOG_FILE = 'userbot.log'

class ModuleManager:
    def __init__(self, client):
        self.client = client
        self.modules = {}
        self.prefix = DEFAULT_PREFIX
        self.start_time = datetime.now()
        self.session_id = str(uuid.uuid4())[:8]
        self.version = self._get_git_version() or "1.0.0"
        self.last_update_time = self._get_last_commit_date() or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        os.makedirs(MODS_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self._setup_logging()

    def _get_git_version(self):
        """Получаем версию из git тегов"""
        try:
            if not os.path.exists('.git'):
                return None
                
            process = os.popen('git describe --tags --abbrev=0 2>/dev/null')
            version = process.read().strip()
            process.close()
            return version if version else None
        except:
            return None

    def _get_last_commit_date(self):
        """Получаем дату последнего коммита"""
        try:
            if not os.path.exists('.git'):
                return None
                
            process = os.popen('git log -1 --format=%cd --date=format:"%Y-%m-%d %H:%M:%S"')
            date = process.read().strip()
            process.close()
            return date if date else None
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

class CoreCommands:
    def __init__(self, manager):
        self.manager = manager
        self.owner_id = None
        self.repo_url = GITHUB_REPO
        self.docs_url = DOCS_URL
        self.connected_services = {
            'Telegram API': True,
            'Translator API': True,
            'Git': os.path.exists('.git')
        }
    
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
        """Получение информации о системе"""
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
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
            return None

    async def handle_info(self, event: Message):
        if not await self.is_owner(event):
            return
            
        me = await self.manager.client.get_me()
        uptime = datetime.now() - self.manager.start_time
        sys_info = self.get_system_info()
        
        info_msg = [
            f"🤖 <b>Acroka UserBot Info</b>",
            "",
            f"👤 <b>Владелец:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>",
            f"🆔 <b>ID:</b> <code>{me.id}</code>",
            f"⏱ <b>Аптайм:</b> {str(timedelta(seconds=uptime.seconds)).split('.')[0]}",
            f"📦 <b>Модулей:</b> {len(self.manager.modules)}",
            f"🔹 <b>Префикс:</b> <code>{self.manager.prefix}</code>",
            "",
            f"🔄 <b>Версия:</b> <code>{self.manager.version}</code>",
            f"📅 <b>Обновлено:</b> <code>{self.manager.last_update_time}</code>",
            ""
        ]
        
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
                "",
                f"⏳ <b>Время работы системы:</b> {sys_info['uptime']}",
                ""
            ])
        
        info_msg.extend([
            "🔗 <b>Подключенные сервисы:</b>",
            *[f"• <b>{service}:</b> {'🟢' if status else '🔴'}" for service, status in self.connected_services.items()],
            "",
            f"📂 <b>Репозиторий:</b> <code>{self.repo_url}</code>",
            f"📝 <b>Документация:</b> <code>{self.docs_url}</code>"
        ])

        await event.edit("\n".join([line for line in info_msg if line]), parse_mode='html', link_preview=False)

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