import asyncio
import os
import sys
import json
import re
import shutil
import platform
import subprocess
from datetime import datetime
from typing import Optional
import aiohttp
from telethon import TelegramClient, events
from telethon.tl.types import Message
from googletrans import Translator

class CoreCommands:
    """Основные команды юзербота"""
    
    def __init__(self, module_manager, client: TelegramClient):
        self.manager = module_manager
        self.client = client
        self.prefix = module_manager.prefix
        self.owner_id = None
        self.start_time = datetime.now()
        
        # Константы
        self.REPO_URL = "https://github.com/theLuni/AcrokaUB"
        self.MODS_REPO = "https://github.com/theLuni/AcrokaUB-Modules"
        self.RAW_MODS_URL = "https://raw.githubusercontent.com/theLuni/AcrokaUB-Modules/main/"
        
    async def register(self):
        """Регистрация всех обработчиков команд"""
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}help$', outgoing=True))
        async def help_handler(event):
            await self.cmd_help(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}info$', outgoing=True))
        async def info_handler(event):
            await self.cmd_info(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}ping$', outgoing=True))
        async def ping_handler(event):
            await self.cmd_ping(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}restart$', outgoing=True))
        async def restart_handler(event):
            await self.cmd_restart(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}update$', outgoing=True))
        async def update_handler(event):
            await self.cmd_update(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}lm$', outgoing=True))
        async def loadmod_handler(event):
            await self.cmd_loadmod(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}ulm (\w+)$', outgoing=True))
        async def unloadmod_handler(event):
            await self.cmd_unloadmod(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}rlm (\w+)$', outgoing=True))
        async def reloadmod_handler(event):
            await self.cmd_reloadmod(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}mlist$', outgoing=True))
        async def modlist_handler(event):
            await self.cmd_modlist(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}dlm (\w+\.py)$', outgoing=True))
        async def downloadmod_handler(event):
            await self.cmd_downloadmod(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}tr (\w+) (.+)$', outgoing=True))
        async def translate_handler(event):
            await self.cmd_translate(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}calc (.+)$', outgoing=True))
        async def calc_handler(event):
            await self.cmd_calc(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}logs$', outgoing=True))
        async def logs_handler(event):
            await self.cmd_logs(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}cfg(?:\s+(.+))?$', outgoing=True))
        async def config_handler(event):
            await self.cmd_config(event)
        
        @self.client.on(events.NewMessage(pattern=rf'^{re.escape(self.prefix)}clean$', outgoing=True))
        async def clean_handler(event):
            await self.cmd_clean(event)
    
    async def is_owner(self, event: Message) -> bool:
        """Проверка, является ли отправитель владельцем"""
        if not self.owner_id:
            me = await self.client.get_me()
            self.owner_id = me.id
        
        return event.sender_id == self.owner_id
    
    async def cmd_help(self, event: Message):
        """Команда помощи"""
        if not await self.is_owner(event):
            return
        
        help_text = f"""
✨ <b>Acroka UserBot v3.0</b> ✨
🔹 <b>Префикс:</b> <code>{self.prefix}</code>

⚙️ <b>Основные команды:</b>
• <code>{self.prefix}help</code> - Это сообщение
• <code>{self.prefix}info</code> - Информация о боте
• <code>{self.prefix}ping</code> - Проверка скорости
• <code>{self.prefix}restart</code> - Перезагрузка
• <code>{self.prefix}update</code> - Обновление бота

📦 <b>Модули:</b>
• <code>{self.prefix}lm</code> - Загрузить модуль (ответ на файл)
• <code>{self.prefix}ulm [имя]</code> - Выгрузить модуль
• <code>{self.prefix}rlm [имя]</code> - Перезагрузить модуль
• <code>{self.prefix}mlist</code> - Список модулей
• <code>{self.prefix}dlm [файл.py]</code> - Скачать модуль

🛠️ <b>Утилиты:</b>
• <code>{self.prefix}tr [язык] [текст]</code> - Переводчик
• <code>{self.prefix}calc [выражение]</code> - Калькулятор
• <code>{self.prefix}logs</code> - Получить логи
• <code>{self.prefix}clean</code> - Очистка кэша

⚙️ <b>Настройки:</b>
• <code>{self.prefix}cfg prefix [префикс]</code> - Сменить префикс
• <code>{self.prefix}cfg</code> - Показать настройки

🔗 <b>Ссылки:</b>
• <a href="{self.REPO_URL}">Репозиторий</a>
• <a href="{self.REPO_URL}/wiki">Документация</a>
"""
        await event.edit(help_text, parse_mode='html')
    
    async def cmd_info(self, event: Message):
        """Информация о боте"""
        if not await self.is_owner(event):
            return
        
        me = await self.client.get_me()
        uptime = datetime.now() - self.start_time
        
        # Получаем информацию о системе
        system_info = self._get_system_info()
        
        info_text = f"""
🤖 <b>Acroka UserBot v3.0</b>

👤 <b>Владелец:</b> <a href='tg://user?id={me.id}'>{me.first_name}</a>
🆔 <b>ID:</b> <code>{me.id}</code>
⏱ <b>Время работы:</b> {str(uptime).split('.')[0]}
📦 <b>Модулей:</b> {len(self.manager.modules)}

⚙️ <b>Система:</b>
• <b>ОС:</b> {system_info['os']}
• <b>Python:</b> {system_info['python']}
• <b>Память:</b> {system_info['memory']}%

🔧 <b>Настройки:</b>
• <b>Префикс:</b> <code>{self.prefix}</code>
• <b>Версия:</b> 3.0
"""
        await event.edit(info_text, parse_mode='html')
    
    def _get_system_info(self) -> dict:
        """Получение информации о системе"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            # Определяем платформу
            if 'ANDROID_ROOT' in os.environ:
                os_name = "Android (Termux)"
            elif 'microsoft' in platform.uname().release.lower():
                os_name = "WSL"
            else:
                os_name = platform.system()
            
            return {
                'os': os_name,
                'python': platform.python_version(),
                'memory': mem.percent
            }
        except:
            return {
                'os': platform.system(),
                'python': platform.python_version(),
                'memory': 'N/A'
            }
    
    async def cmd_ping(self, event: Message):
        """Проверка скорости"""
        if not await self.is_owner(event):
            return
        
        start = datetime.now()
        msg = await event.edit('🏓 Pong!')
        end = datetime.now()
        
        latency = (end - start).microseconds / 1000
        await msg.edit(f'🏓 Pong! | {latency:.2f}ms')
    
    async def cmd_restart(self, event: Message):
        """Перезагрузка бота"""
        if not await self.is_owner(event):
            return
        
        await event.edit('🔄 Перезагрузка...')
        await asyncio.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)
    
    async def cmd_update(self, event: Message):
        """Обновление бота"""
        if not await self.is_owner(event):
            return
        
        try:
            msg = await event.edit('🔄 Проверка обновлений...')
            
            # Временная папка
            temp_dir = 'temp_update'
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            # Клонируем репозиторий
            process = await asyncio.create_subprocess_shell(
                f'git clone {self.REPO_URL} {temp_dir}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode != 0:
                await msg.edit('❌ Ошибка при загрузке обновлений')
                return
            
            # Копируем файлы, сохраняя source
            exclude = {'source', '.git', '__pycache__'}
            
            for item in os.listdir(temp_dir):
                if item not in exclude:
                    src = os.path.join(temp_dir, item)
                    dst = os.path.join('.', item)
                    
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            
            # Обновляем зависимости
            req_file = 'requirements.txt'
            if os.path.exists(req_file):
                await msg.edit('📦 Обновление зависимостей...')
                
                process = await asyncio.create_subprocess_shell(
                    f'{sys.executable} -m pip install -r {req_file} --upgrade',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            # Очистка
            shutil.rmtree(temp_dir)
            
            await msg.edit('✅ Обновление завершено! Перезагрузка...')
            await asyncio.sleep(3)
            os.execl(sys.executable, sys.executable, *sys.argv)
            
        except Exception as e:
            await event.edit(f'❌ Ошибка обновления: {str(e)}')
    
    async def cmd_loadmod(self, event: Message):
        """Загрузка модуля"""
        if not await self.is_owner(event):
            return
        
        if not event.is_reply:
            await event.edit('❌ Ответьте на файл модуля (.py)')
            return
        
        reply = await event.get_reply_message()
        if not reply.file or not reply.file.name.endswith('.py'):
            await event.edit('❌ Файл должен быть Python модулем (.py)')
            return
        
        try:
            msg = await event.edit('⬇️ Скачивание модуля...')
            file_path = await reply.download_media(file='source/mods/')
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            
            if await self.manager.load_module(module_name):
                module_info = self.manager.get_module_info(module_name)
                
                response = [
                    f'✅ <b>Модуль загружен!</b>',
                    f'',
                    f'📦 <b>Имя:</b> {module_info["name"]}',
                    f'🔖 <b>Версия:</b> {module_info["version"]}',
                    f'👤 <b>Автор:</b> {module_info["author"]}',
                    f'',
                    f'📝 <b>Описание:</b>',
                    f'{module_info["description"]}',
                    f'',
                    f'⚙️ <b>Команды:</b>'
                ]
                
                for cmd, desc in module_info['commands'].items():
                    response.append(f'• <code>{self.prefix}{cmd}</code> - {desc}')
                
                await msg.edit('\n'.join(response), parse_mode='html')
            else:
                await msg.edit('❌ Ошибка загрузки модуля')
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            await event.edit(f'❌ Ошибка: {str(e)}')
    
    async def cmd_unloadmod(self, event: Message):
        """Выгрузка модуля"""
        if not await self.is_owner(event):
            return
        
        module_name = event.pattern_match.group(1)
        
        if await self.manager.unload_module(module_name):
            await event.edit(f'✅ Модуль <code>{module_name}</code> выгружен', parse_mode='html')
        else:
            await event.edit(f'❌ Модуль <code>{module_name}</code> не найден', parse_mode='html')
    
    async def cmd_reloadmod(self, event: Message):
        """Перезагрузка модуля"""
        if not await self.is_owner(event):
            return
        
        module_name = event.pattern_match.group(1)
        
        if await self.manager.reload_module(module_name):
            await event.edit(f'✅ Модуль <code>{module_name}</code> перезагружен', parse_mode='html')
        else:
            await event.edit(f'❌ Ошибка перезагрузки модуля <code>{module_name}</code>', parse_mode='html')
    
    async def cmd_modlist(self, event: Message):
        """Список модулей"""
        if not await self.is_owner(event):
            return
        
        modules = self.manager.list_modules()
        
        if not modules:
            await event.edit('ℹ️ Нет загруженных модулей')
            return
        
        response = [f'📦 <b>Загруженные модули ({len(modules)})</b>', '']
        
        for module in modules:
            uptime = datetime.now() - module['loaded_at']
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            response.extend([
                f'🔹 <b>{module["name"]}</b> v{module["version"]}',
                f'   ├ <i>{module["description"][:50]}...</i>',
                f'   ├ 👤 {module["author"]}',
                f'   ├ 🕒 {hours}ч {minutes}м назад',
                f'   └ ⚙️ {len(module["commands"])} команд',
                ''
            ])
        
        response.append('🚀 Используйте команды .ulm/.rlm для управления')
        
        await event.edit('\n'.join(response), parse_mode='html')
    
    async def cmd_downloadmod(self, event: Message):
        """Скачивание модуля из репозитория"""
        if not await self.is_owner(event):
            return
        
        module_file = event.pattern_match.group(1)
        
        try:
            msg = await event.edit(f'⬇️ Скачивание {module_file}...')
            
            url = f'{self.RAW_MODS_URL}{module_file}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        await msg.edit(f'❌ Модуль не найден: {module_file}')
                        return
                    
                    content = await response.read()
            
            # Сохраняем файл
            file_path = f'source/mods/{module_file}'
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Загружаем модуль
            module_name = os.path.splitext(module_file)[0]
            if await self.manager.load_module(module_name):
                await msg.edit(f'✅ Модуль <code>{module_name}</code> успешно установлен!', parse_mode='html')
            else:
                await msg.edit(f'⚠️ Модуль скачан, но не загружен: {module_file}')
                
        except Exception as e:
            await event.edit(f'❌ Ошибка: {str(e)}')
    
    async def cmd_translate(self, event: Message):
        """Перевод текста"""
        if not await self.is_owner(event):
            return
        
        target_lang = event.pattern_match.group(1)
        text = event.pattern_match.group(2)
        
        try:
            translator = Translator()
            translated = translator.translate(text, dest=target_lang)
            
            await event.edit(
                f'🌐 Перевод ({translated.src} → {target_lang}):\n\n'
                f'{translated.text}'
            )
        except Exception as e:
            await event.edit(f'❌ Ошибка перевода: {str(e)}')
    
    async def cmd_calc(self, event: Message):
        """Калькулятор"""
        if not await self.is_owner(event):
            return
        
        expr = event.pattern_match.group(1)
        
        try:
            # Безопасное вычисление
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expr):
                await event.edit('❌ Недопустимые символы в выражении')
                return
            
            result = eval(expr)
            await event.edit(f'🧮 {expr} = {result}')
        except Exception as e:
            await event.edit(f'❌ Ошибка вычисления: {str(e)}')
    
    async def cmd_logs(self, event: Message):
        """Получение логов"""
        if not await self.is_owner(event):
            return
        
        log_file = 'userbot.log'
        
        if not os.path.exists(log_file):
            await event.edit('ℹ️ Файл логов не найден')
            return
        
        try:
            await event.delete()
            await self.client.send_file(
                event.chat_id,
                log_file,
                caption='📄 Логи юзербота'
            )
        except Exception as e:
            await event.edit(f'❌ Ошибка отправки логов: {str(e)}')
    
    async def cmd_config(self, event: Message):
        """Управление настройками"""
        if not await self.is_owner(event):
            return
        
        args = event.pattern_match.group(1)
        
        if not args:
            # Показать текущие настройки
            settings = self._get_current_settings()
            await event.edit(settings, parse_mode='html')
            return
        
        parts = args.split(' ', 1)
        setting = parts[0].lower()
        value = parts[1] if len(parts) > 1 else None
        
        if setting == 'prefix':
            if not value:
                await event.edit(f'ℹ️ Текущий префикс: <code>{self.prefix}</code>', parse_mode='html')
                return
            
            if len(value) > 3:
                await event.edit('❌ Префикс должен быть не более 3 символов')
                return
            
            # Сохраняем новый префикс
            with open('source/prefix.txt', 'w') as f:
                f.write(value)
            
            await event.edit(f'✅ Префикс изменен на: <code>{value}</code>\nПерезапустите бота для применения.', parse_mode='html')
        
        else:
            await event.edit('❌ Неизвестная настройка')
    
    def _get_current_settings(self) -> str:
        """Получение текущих настроек"""
        return f"""
⚙️ <b>Текущие настройки</b>

🔤 <b>Префикс команд:</b> <code>{self.prefix}</code>
📁 <b>Папка модулей:</b> source/mods/
📦 <b>Загружено модулей:</b> {len(self.manager.modules)}

🔄 <b>Для изменения:</b>
• <code>{self.prefix}cfg prefix [новый]</code> - Сменить префикс
"""
    
    async def cmd_clean(self, event: Message):
        """Очистка кэша"""
        if not await self.is_owner(event):
            return
        
        try:
            msg = await event.edit('🧹 Очистка кэша...')
            
            # Очищаем __pycache__
            for root, dirs, files in os.walk('.'):
                if '__pycache__' in dirs:
                    cache_dir = os.path.join(root, '__pycache__')
                    shutil.rmtree(cache_dir)
            
            # Удаляем .pyc файлы
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.endswith('.pyc'):
                        os.remove(os.path.join(root, file))
            
            await msg.edit('✅ Кэш успешно очищен!')
            
        except Exception as e:
            await event.edit(f'❌ Ошибка очистки: {str(e)}')