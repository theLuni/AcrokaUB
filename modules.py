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

class ModuleManager:
    def __init__(self, client):
        self.client = client
        self.modules = {}
        self.prefix = DEFAULT_PREFIX
        self.start_time = datetime.now()
        os.makedirs(MODS_DIR, exist_ok=True)

    async def load_module(self, module_name: str) -> bool:
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
        cache_dir = os.path.join(MODS_DIR, '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        pyc_file = os.path.join(MODS_DIR, f"{module_name}.pyc")
        if os.path.exists(pyc_file):
            os.remove(pyc_file)

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
    
    async def initialize(self):
        me = await self.manager.client.get_me()
        self.owner_id = me.id
        print(f"🔐 [Система] Владелец ID: {self.owner_id}")

    async def is_owner(self, event: Message) -> bool:
        if event.sender_id == self.owner_id:
            return True
        try:
            await event.delete()
        except:
            pass
        return False

    def get_memory_usage(self):
        """Получение информации об использовании памяти"""
        try:
            return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)
        except:
            return "N/A"

    def get_disk_usage(self):
        """Получение информации о диске"""
        try:
            usage = psutil.disk_usage('/')
            return f"{usage.percent}% (свободно: {round(usage.free / 1024 / 1024)} MB)"
        except:
            return "N/A"

    async def handle_help(self, event: Message):
        if not await self.is_owner(event):
            return
            
        prefix = self.manager.prefix
        
        help_msg = [
            "✨ <b>Acroka UserBot Help</b> ✨",
            "",
            "⚙️ <b>Основные команды:</b>",
            f"• <code>{prefix}help</code> - Показать это сообщение",
            f"• <code>{prefix}ping</code> - Проверка пинга",
            f"• <code>{prefix}info</code> - Информация о боте",
            f"• <code>{prefix}update</code> - Обновить бота",
            "",
            "📦 <b>Управление модулями:</b>",
            f"• <code>{prefix}loadmod</code> - Загрузить модуль",
            f"• <code>{prefix}getmod [name]</code> - Получить модуль",
            f"• <code>{prefix}unloadmod [name]</code> - Удалить модуль",
            f"• <code>{prefix}modlist</code> - Список модулей",
            "",
            "🛠️ <b>Утилиты:</b>",
            f"• <code>{prefix}tr [lang]</code> - Переводчик",
            f"• <code>{prefix}calc [expr]</code> - Калькулятор",
            f"• <code>{prefix}clean</code> - Очистка кэша"
        ]
        
        if self.manager.modules:
            help_msg.extend(["", "🔌 <b>Загруженные модули:</b>"])
            for mod_name in self.manager.modules.keys():
                help_msg.append(f"• <code>{mod_name}</code>")

        await event.edit("\n".join(help_msg), parse_mode='html')

    async def handle_ping(self, event: Message):
        """Обработчик команды ping"""
        if not await self.is_owner(event):
            return
            
        start = datetime.now()
        msg = await event.edit("🏓 Pong!")
        latency = (datetime.now() - start).microseconds / 1000
        await msg.edit(f"🏓 Pong! | {latency}ms")

    async def handle_info(self, event: Message):
        if not await self.is_owner(event):
            return
            
        me = await self.manager.client.get_me()
        uptime = datetime.now() - self.manager.start_time
        
        sys_info = [
            f"<b>ОС:</b> {platform.system()} {platform.release()}",
            f"<b>Python:</b> {platform.python_version()}",
            f"<b>Telethon:</b> {telethon.__version__}",
            f"<b>Память:</b> {self.get_memory_usage()} MB",
            f"<b>Диск:</b> {self.get_disk_usage()}"
        ]
        
        info_msg = [
            "🤖 <b>Acroka UserBot Info</b>",
            "",
            f"👤 <b>Владелец:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>",
            f"🆔 <b>ID:</b> <code>{me.id}</code>",
            f"⏱ <b>Аптайм:</b> {str(timedelta(seconds=uptime.seconds)).split('.')[0]}",
            f"📦 <b>Модулей:</b> {len(self.manager.modules)}",
            "",
            "⚙️ <b>Система:</b>",
            *sys_info,
            "",
            f"🔗 <b>Репозиторий:</b> <code>{self.repo_url}</code>"
        ]

        await event.edit("\n".join(info_msg), parse_mode='html', link_preview=False)

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
                    f"2. Файл удален: <code>{os.path.basename(module_path)}</code>",
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
            
        mod_list = ["📦 <b>Загруженные модули:</b>", ""]
        
        for mod_name, mod_data in self.manager.modules.items():
            module = mod_data['module']
            desc = getattr(module, '__doc__', 'Без описания').split('\n')[0]
            version = getattr(module, 'version', '1.0')
            
            mod_list.append(
                f"• <b>{mod_name}</b> (v{version})\n"
                f"  <i>{desc}</i>"
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
            (rf'^{prefix}modlist$', self.handle_modlist),
            (rf'^{prefix}tr (\w+)$', self.handle_translate),
            (rf'^{prefix}calc (.+)$', self.handle_calc),
            (rf'^{prefix}restart$', self.restart_bot),
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