import os
import sys
import importlib
import asyncio
import re
import shutil
import traceback
import platform
import telethon
from datetime import datetime
from telethon import TelegramClient, events
from config import API_ID, API_HASH, BOT_TOKEN

# ====================== КОНСТАНТЫ ======================
MODS_DIR = 'source/mods/'
PREFIX_FILE = 'source/prefix.txt'
DEFAULT_PREFIX = '.'
LOADED_MODS_FILE = '.loaded_mods'
GIF_URL = "https://tenor.com/vzU4iQebtgZ.gif"
GIF_FILENAME = "welcome.gif"

# ====================== МЕНЕДЖЕР МОДУЛЕЙ ======================
class ModuleManager:
    def __init__(self, client):
        self.client = client
        self.modules = {}
        self.prefix = DEFAULT_PREFIX
        self.start_time = datetime.now()
        self.stats = {
            'received': 0,
            'sent': 0,
            'active_users': set()
        }
        os.makedirs(MODS_DIR, exist_ok=True)

    def set_prefix(self, prefix):
        self.prefix = prefix

    async def load_module(self, module_name):
        """Загрузка модуля с полной изоляцией"""
        try:
            self._clean_cache(module_name)
            module_path = os.path.join(MODS_DIR, f"{module_name}.py")
            
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
                'loaded_at': datetime.now()
            }
            
            print(f"✅ [Модуль] {module_name} успешно загружен")
            return True
            
        except Exception as e:
            print(f"❌ [Ошибка] Не удалось загрузить модуль {module_name}:")
            traceback.print_exc()
            return False

    async def unload_module(self, module_name):
        """Полная выгрузка модуля"""
        if module_name not in self.modules:
            return False
            
        module_data = self.modules[module_name]
        
        try:
            if hasattr(module_data['module'], 'on_unload'):
                await module_data['module'].on_unload()
            
            for handler in module_data['handlers']:
                try:
                    self.client.remove_event_handler(handler)
                except:
                    pass
            
            del sys.modules[f"userbot.mods.{module_name}"]
            del self.modules[module_name]
            
            import gc
            gc.collect()
            
            print(f"✅ [Модуль] {module_name} выгружен")
            return True
            
        except Exception as e:
            print(f"❌ [Ошибка] Не удалось выгрузить модуль {module_name}:")
            traceback.print_exc()
            return False

    async def reload_module(self, module_name):
        await self.unload_module(module_name)
        return await self.load_module(module_name)

    def _clean_cache(self, module_name):
        """Очистка кэша модуля"""
        cache_dir = os.path.join(MODS_DIR, '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        pyc_file = os.path.join(MODS_DIR, f"{module_name}.pyc")
        if os.path.exists(pyc_file):
            os.remove(pyc_file)

    def get_module_info(self, module_name):
        """Получение информации о модуле"""
        if module_name not in self.modules:
            return None
            
        try:
            with open(self.modules[module_name]['path'], 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(5)]
                
            info = {
                'name': module_name,
                'commands': 'Нет информации',
                'description': 'Нет описания',
                'version': '1.0'
            }
            
            for line in lines:
                if line.startswith('# name:'):
                    info['name'] = line[7:].strip()
                elif line.startswith('# commands:'):
                    info['commands'] = line[11:].strip()
                elif line.startswith('# desc:'):
                    info['description'] = line[6:].strip()
                elif line.startswith('# version:'):
                    info['version'] = line[9:].strip()
            
            return info
        except:
            return {
                'name': module_name,
                'commands': 'Неизвестно',
                'description': 'Нет информации',
                'version': '1.0'
            }

    async def load_all_modules(self):
        """Загрузка всех модулей из директории"""
        print(f"🔍 [Система] Сканирование папки модулей...")
        
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
        """Сохранение списка загруженных модулей"""
        with open(LOADED_MODS_FILE, 'w') as f:
            f.write('\n'.join(self.modules.keys()))

# ====================== КОМАНДЫ ЯДРА ======================
class CoreCommands:
    def __init__(self, manager):
        self.manager = manager
    
    async def is_owner(self, event):
        """Проверка владельца бота"""
        me = await event.client.get_me()
        return event.sender_id == me.id
    
    async def update_bot(self, event):
        """Обновление бота из репозитория"""
        if not await self.is_owner(event):
            return
            
        try:
            await event.edit("🔄 [Система] Проверка обновлений...")
            
            # Клонирование репозитория
            repo_url = "https://github.com/theLuni/AcrokaUB.git"
            temp_dir = "temp_update"
            
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            os.makedirs(temp_dir, exist_ok=True)
            
            # Выполнение git-команд
            cmds = [
                ['git', 'clone', repo_url, temp_dir],
                ['cp', '-r', f'{temp_dir}/*', '.'],
                ['rm', '-rf', temp_dir]
            ]
            
            for cmd in cmds:
                proc = await asyncio.create_subprocess_exec(*cmd)
                await proc.wait()
            
            await event.edit("✅ [Система] Бот успешно обновлен! Перезагрузка...")
            await self.restart_bot(event)
            
        except Exception as e:
            await event.edit(f"❌ [Ошибка] Не удалось обновить бота:\n{str(e)}")

    async def get_module(self, event):
        """Отправка модуля пользователю"""
        if not await self.is_owner(event):
            return
            
        module_name = event.pattern_match.group(1)
        
        if module_name not in self.manager.modules:
            await event.edit(f"❌ [Модуль] {module_name} не найден")
            return
            
        try:
            module_path = self.manager.modules[module_name]['path']
            await event.client.send_file(
                event.chat_id,
                module_path,
                caption=f"📦 Модуль: {module_name}",
                reply_to=event.id
            )
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ [Ошибка] Не удалось отправить модуль:\n{str(e)}")

    async def restart_bot(self, event=None):
        """Перезагрузка бота"""
        if event and not await self.is_owner(event):
            return
            
        if event:
            await event.edit("🔄 [Система] Перезагрузка...")
        
        await self.manager.save_loaded_modules()
        os.execl(sys.executable, sys.executable, *sys.argv)

    async def handle_help(self, event):
        """Показ списка команд"""
        if not await self.is_owner(event):
            return
        
        self.manager.stats['received'] += 1
        self.manager.stats['active_users'].add(event.sender_id)

        prefix = self.manager.prefix
        base_commands = [
            f"📜 {prefix}info - Информация о боте",
            f"🏓 {prefix}ping - Проверка пинга",
            f"📦 {prefix}loadmod - Загрузить модуль (ответ на файл)",
            f"🗑️ {prefix}unloadmod <имя> - Выгрузить модуль",
            f"🔄 {prefix}reloadmod <имя> - Перезагрузить модуль",
            f"📤 {prefix}getmod <имя> - Получить файл модуля",
            f"🔄 {prefix}update - Обновить бота",
            f"⚙️ {prefix}setprefix <символ> - Изменить префикс",
            f"🔄 {prefix}restart - Перезапустить бота",
            f"📋 {prefix}modules - Список модулей"
        ]

        message = "✨ <b>Доступные команды:</b>\n"
        message += f"<code>Префикс: '{prefix}'</code>\n\n"
        
        message += "🔹 <b>Основные команды:</b>\n"
        message += "\n".join(f"• {cmd}" for cmd in base_commands)
        
        if self.manager.modules:
            message += "\n\n🔹 <b>Модули:</b>\n"
            for name in self.manager.modules:
                info = self.manager.get_module_info(name)
                message += f"• <code>{name}</code> - {info['commands']}\n"
        
        await event.edit(message, parse_mode='html')

    def register_handlers(self):
        """Регистрация обработчиков команд"""
        prefix = re.escape(self.manager.prefix)
        
        cmd_handlers = [
            (rf'^{prefix}help$', self.handle_help),
            (rf'^{prefix}update$', self.update_bot),
            (rf'^{prefix}getmod (\w+)$', self.get_module),
            (rf'^{prefix}restart$', self.restart_bot),
        ]
        
        for pattern, handler in cmd_handlers:
            self.manager.client.add_event_handler(
                handler,
                events.NewMessage(pattern=pattern, outgoing=False)
            )

# ====================== ЗАПУСК БОТА ======================
async def main():
    # Инициализация клиента
    client = TelegramClient('userbot_session', API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)
    print("✅ [Система] Бот авторизован")

    # Загрузка префикса
    prefix = DEFAULT_PREFIX
    if os.path.exists(PREFIX_FILE):
        with open(PREFIX_FILE, 'r') as f:
            prefix = f.read().strip() or DEFAULT_PREFIX

    # Инициализация менеджера модулей
    manager = ModuleManager(client)
    manager.set_prefix(prefix)
    await manager.load_all_modules()

    # Регистрация команд ядра
    CoreCommands(manager).register_handlers()

    print("🟢 [Система] Бот запущен и готов к работе")
    try:
        await client.run_until_disconnected()
    finally:
        await manager.save_loaded_modules()
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
