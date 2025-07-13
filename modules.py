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
from telethon.tl.types import Message
from config import API_ID, API_HASH
import requests
from googletrans import Translator

# ====================== КОНСТАНТЫ ======================
MODS_DIR = 'source/mods/'
PREFIX_FILE = 'source/prefix.txt'
DEFAULT_PREFIX = '.'
LOADED_MODS_FILE = '.loaded_mods'
SESSION_FILE = 'userbot_session'

# ====================== МЕНЕДЖЕР МОДУЛЕЙ ======================
class ModuleManager:
    def __init__(self, client):
        self.client = client
        self.modules = {}
        self.prefix = DEFAULT_PREFIX
        self.start_time = datetime.now()
        os.makedirs(MODS_DIR, exist_ok=True)

    async def load_module(self, module_name: str) -> bool:
        """Загрузка модуля с обработкой ошибок"""
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

    async def unload_module(self, module_name: str) -> bool:
        """Выгрузка модуля с очисткой"""
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
            
            print(f"✅ [Модуль] {module_name} выгружен")
            return True
            
        except Exception as e:
            print(f"❌ [Ошибка] Не удалось выгрузить модуль {module_name}:")
            traceback.print_exc()
            return False

    def _clean_cache(self, module_name: str):
        """Очистка кэша модуля"""
        cache_dir = os.path.join(MODS_DIR, '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        pyc_file = os.path.join(MODS_DIR, f"{module_name}.pyc")
        if os.path.exists(pyc_file):
            os.remove(pyc_file)

    async def load_all_modules(self):
        """Загрузка всех модулей из директории"""
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
        """Сохранение списка модулей"""
        with open(LOADED_MODS_FILE, 'w') as f:
            f.write('\n'.join(self.modules.keys()))

# ====================== ОСНОВНЫЕ КОМАНДЫ ======================
class CoreCommands:
    def __init__(self, manager):
        self.manager = manager
        self.owner_id = None
    
    async def initialize(self):
        """Инициализация владельца"""
        me = await self.manager.client.get_me()
        self.owner_id = me.id
        print(f"🔐 [Система] Владелец ID: {self.owner_id}")

    async def is_owner(self, event: Message) -> bool:
        """Проверка прав владельца"""
        if event.sender_id == self.owner_id:
            return True
        try:
            await event.delete()
        except:
            pass
        return False

    async def handle_help(self, event: Message):
        """Обработчик команды помощи"""
        if not await self.is_owner(event):
            return
            
        prefix = self.manager.prefix
        commands = [
            f"{prefix}help - Список команд",
            f"{prefix}ping - Проверка работоспособности",
            f"{prefix}info - Информация о юзерботе",
            f"{prefix}loadmod - Загрузить модуль (ответ на файл)",
            f"{prefix}unloadmod <имя> - Выгрузить модуль",
            f"{prefix}restart - Перезапуск юзербота",
            f"{prefix}tr <язык> - Переводчик",
            f"{prefix}calc <выражение> - Калькулятор"
        ]
        
        await event.edit(
            "✨ <b>Доступные команды:</b>\n" + 
            "\n".join(f"• {cmd}" for cmd in commands),
            parse_mode='html'
        )

    async def handle_ping(self, event: Message):
        """Проверка пинга"""
        if not await self.is_owner(event):
            return
            
        start = datetime.now()
        msg = await event.edit("🏓 Pong!")
        latency = (datetime.now() - start).microseconds / 1000
        await msg.edit(f"🏓 Pong! | {latency}ms")

    async def handle_info(self, event: Message):
        """Информация о юзерботе"""
        if not await self.is_owner(event):
            return
            
        me = await self.manager.client.get_me()
        uptime = datetime.now() - self.manager.start_time
        
        await event.edit(
            f"🤖 <b>UserBot Info</b>\n\n"
            f"👤 <b>Владелец:</b> {me.first_name}\n"
            f"🆔 <b>ID:</b> {me.id}\n"
            f"⏱ <b>Аптайм:</b> {str(uptime).split('.')[0]}\n"
            f"⚙️ <b>Версия Telethon:</b> {telethon.__version__}\n"
            f"📦 <b>Модулей:</b> {len(self.manager.modules)}",
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
                await event.edit(f"✅ Модуль {module_name} загружен!")
            else:
                await event.edit(f"❌ Ошибка загрузки модуля")
                
        except Exception as e:
            await event.edit(f"❌ Ошибка: {str(e)}")
            if os.path.exists(path):
                os.remove(path)

    async def handle_unloadmod(self, event: Message):
        """Выгрузка модуля"""
        if not await self.is_owner(event):
            return
            
        module_name = event.pattern_match.group(1)
        if module_name not in self.manager.modules:
            await event.edit(f"❌ Модуль {module_name} не найден")
            return
            
        if await self.manager.unload_module(module_name):
            await event.edit(f"✅ Модуль {module_name} выгружен")
        else:
            await event.edit(f"❌ Ошибка выгрузки модуля")

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
        """Регистрация обработчиков команд"""
        prefix = re.escape(self.manager.prefix)
        
        cmd_handlers = [
            (rf'^{prefix}help$', self.handle_help),
            (rf'^{prefix}ping$', self.handle_ping),
            (rf'^{prefix}info$', self.handle_info),
            (rf'^{prefix}loadmod$', self.handle_loadmod),
            (rf'^{prefix}unloadmod (\w+)$', self.handle_unloadmod),
            (rf'^{prefix}tr (\w+)$', self.handle_translate),
            (rf'^{prefix}calc (.+)$', self.handle_calc),
            (rf'^{prefix}restart$', self.restart_bot),
        ]
        
        for pattern, handler in cmd_handlers:
            self.manager.client.add_event_handler(
                handler,
                events.NewMessage(pattern=pattern, outgoing=True)
            )

# ====================== ЗАПУСК ЮЗЕРБОТА ======================
async def main(client=None):
    # Инициализация клиента
    if client is None:
        client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
        try:
            await client.start()
            print("✅ [Система] Юзербот авторизован")
        except Exception as e:
            print(f"❌ [Ошибка авторизации] {str(e)}")
            return
    
    try:
        # Загрузка префикса
        prefix = DEFAULT_PREFIX
        if os.path.exists(PREFIX_FILE):
            with open(PREFIX_FILE, 'r') as f:
                prefix = f.read().strip() or DEFAULT_PREFIX

        # Инициализация менеджера модулей
        manager = ModuleManager(client)
        manager.prefix = prefix
        
        # Инициализация команд
        core_commands = CoreCommands(manager)
        await core_commands.initialize()
        core_commands.register_handlers()

        # Загрузка модулей
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
