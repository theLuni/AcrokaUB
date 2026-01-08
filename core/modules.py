import asyncio
import os
import sys
import json
import re
import shutil
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import Message

# Константы
BASE_DIR = Path(__file__).parent.parent
MODS_DIR = BASE_DIR / 'source' / 'mods'
CONFIG_DIR = BASE_DIR / 'config'
LOG_FILE = BASE_DIR / 'userbot.log'
PREFIX_FILE = BASE_DIR / 'source' / 'prefix.txt'
DEFAULT_PREFIX = '.'
BACKUP_DIR = BASE_DIR / 'source' / 'backups'

# Создаем необходимые директории
for dir_path in [MODS_DIR, CONFIG_DIR, BACKUP_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

class Module:
    """Базовый класс для модулей"""
    name: str = "Unnamed Module"
    version: str = "1.0"
    author: str = "Unknown"
    description: str = "No description provided"
    commands: Dict[str, str] = {}
    dependencies: List[str] = []
    
    def __init__(self, client: TelegramClient, prefix: str):
        self.client = client
        self.prefix = prefix
        self.handlers = []
    
    async def on_load(self):
        """Вызывается при загрузке модуля"""
        pass
    
    async def on_unload(self):
        """Вызывается при выгрузке модуля"""
        pass

class ModuleManager:
    """Менеджер модулей"""
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.modules: Dict[str, Dict] = {}
        self.prefix = self._load_prefix()
        self.logger = self._setup_logging()
    
    def _load_prefix(self) -> str:
        """Загрузка префикса из файла"""
        try:
            if PREFIX_FILE.exists():
                prefix = PREFIX_FILE.read_text().strip()
                return prefix if 0 < len(prefix) <= 3 else DEFAULT_PREFIX
        except Exception:
            pass
        return DEFAULT_PREFIX
    
    def _setup_logging(self):
        """Настройка логирования"""
        import logging
        logger = logging.getLogger('AcrokaUB')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # Файловый обработчик
            file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(file_handler)
            
            # Консольный обработчик
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s: %(message)s'
            ))
            logger.addHandler(console_handler)
        
        return logger
    
    async def load_module(self, module_name: str) -> bool:
        """Загрузка модуля"""
        try:
            module_path = MODS_DIR / f"{module_name}.py"
            
            if not module_path.exists():
                self.logger.error(f"Module {module_name} not found")
                return False
            
            # Создаем резервную копию
            await self._create_backup(module_path)
            
            # Проверяем зависимости
            if not await self._check_dependencies(module_path):
                return False
            
            # Загружаем модуль
            spec = importlib.util.spec_from_file_location(
                f"modules.{module_name}",
                module_path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            
            # Исполняем модуль
            spec.loader.exec_module(module)
            
            # Ищем класс модуля
            module_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Module) and 
                    obj != Module):
                    module_class = obj
                    break
            
            if not module_class:
                self.logger.error(f"No Module class found in {module_name}")
                return False
            
            # Создаем экземпляр модуля
            module_instance = module_class(self.client, self.prefix)
            
            # Регистрируем обработчики команд
            handlers = []
            for cmd, description in module_instance.commands.items():
                pattern = rf'^{re.escape(self.prefix)}{cmd}$'
                handler = module_instance.__class__.__dict__.get(cmd)
                
                if handler and callable(handler):
                    @self.client.on(events.NewMessage(pattern=pattern, outgoing=True))
                    async def handler_wrapper(event, cmd_handler=handler):
                        await cmd_handler(module_instance, event)
                    
                    handlers.append(handler_wrapper)
            
            # Сохраняем информацию о модуле
            self.modules[module_name] = {
                'instance': module_instance,
                'class': module_class,
                'path': module_path,
                'handlers': handlers,
                'loaded_at': datetime.now(),
                'info': {
                    'name': module_instance.name,
                    'version': module_instance.version,
                    'author': module_instance.author,
                    'description': module_instance.description,
                    'commands': module_instance.commands
                }
            }
            
            # Вызываем on_load
            await module_instance.on_load()
            
            self.logger.info(f"Module {module_name} loaded successfully")
            print(f"✅ [Модуль] {module_name} v{module_instance.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading module {module_name}: {e}", exc_info=True)
            return False
    
    async def _create_backup(self, module_path: Path):
        """Создание резервной копии модуля"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = BACKUP_DIR / f"{module_path.stem}_{timestamp}.py"
            shutil.copy2(module_path, backup_file)
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
    
    async def _check_dependencies(self, module_path: Path) -> bool:
        """Проверка и установка зависимостей"""
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем зависимости в комментариях
            deps_match = re.search(r'#\s*dependencies?:\s*(.+)', content)
            if not deps_match:
                return True
            
            dependencies = [d.strip() for d in deps_match.group(1).split(',')]
            if not dependencies:
                return True
            
            print(f"📦 Установка зависимостей: {', '.join(dependencies)}")
            
            # Устанавливаем зависимости
            process = await asyncio.create_subprocess_shell(
                f'{sys.executable} -m pip install {" ".join(dependencies)}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Dependency installation failed: {stderr.decode()}")
                return False
            
            self.logger.info(f"Dependencies installed: {dependencies}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking dependencies: {e}")
            return False
    
    async def unload_module(self, module_name: str) -> bool:
        """Выгрузка модуля"""
        if module_name not in self.modules:
            return False
        
        try:
            module_data = self.modules[module_name]
            
            # Вызываем on_unload
            await module_data['instance'].on_unload()
            
            # Удаляем обработчики
            for handler in module_data['handlers']:
                self.client.remove_event_handler(handler)
            
            # Удаляем из кэша
            module_key = f"modules.{module_name}"
            if module_key in sys.modules:
                del sys.modules[module_key]
            
            # Удаляем из словаря модулей
            del self.modules[module_name]
            
            self.logger.info(f"Module {module_name} unloaded")
            print(f"🔴 [Модуль] {module_name} выгружен")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unloading module {module_name}: {e}")
            return False
    
    async def reload_module(self, module_name: str) -> bool:
        """Перезагрузка модуля"""
        if await self.unload_module(module_name):
            return await self.load_module(module_name)
        return False
    
    async def load_all_modules(self):
        """Загрузка всех модулей"""
        print("\n" + "📦 ЗАГРУЗКА МОДУЛЕЙ".center(50, '─'))
        
        module_count = 0
        for file in MODS_DIR.glob("*.py"):
            if file.name.startswith('_'):
                continue
            
            module_name = file.stem
            if await self.load_module(module_name):
                module_count += 1
        
        print(f"✅ Загружено модулей: {module_count}")
        print("─" * 50)
    
    def get_module_info(self, module_name: str) -> Optional[Dict]:
        """Получение информации о модуле"""
        return self.modules.get(module_name, {}).get('info')
    
    def list_modules(self) -> List[Dict]:
        """Список всех модулей"""
        return [
            {
                'name': name,
                **data['info'],
                'loaded_at': data['loaded_at']
            }
            for name, data in self.modules.items()
        ]

async def load_modules(client: TelegramClient):
    """Основная функция загрузки модулей"""
    manager = ModuleManager(client)
    await manager.load_all_modules()
    
    # Загружаем основные команды
    from core.commands import CoreCommands
    core_cmds = CoreCommands(manager, client)
    await core_cmds.register()
    
    return manager
