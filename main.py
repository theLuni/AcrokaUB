#!/usr/bin/env python3
"""
Acroka UserBot v3.0
Мощный и гибкий юзербот для Telegram
"""

import asyncio
import sys
import os
import traceback
from pathlib import Path
from colorama import init, Fore, Style

# Добавляем путь к проекту в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Инициализация colorama для цветного вывода
init(autoreset=True)

def print_banner():
    """Вывод баннера"""
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
    ╔═══════════════════════════════════════╗
    ║          {Fore.YELLOW}Acroka UserBot v3.0{Fore.CYAN}          ║
    ║    {Fore.WHITE}Мощный юзербот для Telegram{Fore.CYAN}      ║
    ╚═══════════════════════════════════════╝
{Style.RESET_ALL}
    """
    print(banner)

def check_dependencies():
    """Проверка зависимостей"""
    print(f"{Fore.YELLOW}🔍 Проверка зависимостей...{Style.RESET_ALL}")
    
    required_dirs = [
        'source',
        'source/mods',
        'source/backups',
        'config'
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            print(f"{Fore.BLUE}📁 Создаем папку: {dir_path}{Style.RESET_ALL}")
            path.mkdir(parents=True, exist_ok=True)
    
    # Проверяем наличие requirements.txt
    if not Path('requirements.txt').exists():
        print(f"{Fore.YELLOW}⚠️ Файл requirements.txt не найден{Style.RESET_ALL}")
        
        # Создаем минимальный requirements.txt
        with open('requirements.txt', 'w') as f:
            f.write("""telethon==1.40.0
requests==2.32.4
aiohttp==3.12.13
psutil==7.0.0
pytz==2025.2
beautifulsoup4==4.12.3
googletrans==4.0.0rc1
colorama==0.4.6
Pillow==10.4.0
python-dotenv==1.0.1""")
        
        print(f"{Fore.GREEN}✅ Создан файл requirements.txt{Style.RESET_ALL}")
    
    return True

async def load_modules_directly(client):
    """Прямая загрузка модулей (обходная функция)"""
    print(f"{Fore.CYAN}📦 Загрузка модулей...{Style.RESET_ALL}")
    
    try:
        # Пробуем импортировать из новой структуры
        try:
            from core.modules import load_modules
            manager = await load_modules(client)
            print(f"{Fore.GREEN}✅ Модули загружены (новая структура){Style.RESET_ALL}")
            return manager
        except ImportError as e:
            print(f"{Fore.YELLOW}⚠️ Не удалось загрузить модули через core: {e}{Style.RESET_ALL}")
            
            # Пробуем старый способ
            print(f"{Fore.CYAN}🔄 Пробуем загрузить модули напрямую...{Style.RESET_ALL}")
            
            from telethon import events
            import re
            
            # Создаем простой менеджер модулей на месте
            class SimpleModuleManager:
                def __init__(self, client):
                    self.client = client
                    self.modules = {}
                    self.prefix = self._load_prefix()
                
                def _load_prefix(self):
                    prefix_file = Path('source/prefix.txt')
                    if prefix_file.exists():
                        try:
                            prefix = prefix_file.read_text().strip()
                            return prefix if 0 < len(prefix) <= 3 else '.'
                        except:
                            pass
                    return '.'
            
            manager = SimpleModuleManager(client)
            
            # Загружаем базовые команды
            @client.on(events.NewMessage(pattern=rf'^{re.escape(manager.prefix)}help$', outgoing=True))
            async def help_handler(event):
                await event.edit(f"""
🤖 <b>Acroka UserBot</b>

🔹 <b>Префикс:</b> <code>{manager.prefix}</code>

⚙️ <b>Основные команды:</b>
• <code>{manager.prefix}help</code> - Справка
• <code>{manager.prefix}ping</code> - Проверка
• <code>{manager.prefix}restart</code> - Перезагрузка

ℹ️ <b>Статус:</b> Модули загружены в упрощенном режиме
                """, parse_mode='html')
            
            @client.on(events.NewMessage(pattern=rf'^{re.escape(manager.prefix)}ping$', outgoing=True))
            async def ping_handler(event):
                import time
                start = time.time()
                msg = await event.edit('🏓 Pong!')
                end = time.time()
                latency = (end - start) * 1000
                await msg.edit(f'🏓 Pong! | {latency:.2f}ms')
            
            print(f"{Fore.GREEN}✅ Базовые команды загружены{Style.RESET_ALL}")
            return manager
            
    except Exception as e:
        print(f"{Fore.RED}❌ Ошибка при загрузке модулей: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        return None

async def main():
    """Основная функция запуска"""
    print_banner()
    
    if not check_dependencies():
        print(f"{Fore.RED}❌ Не удалось проверить зависимости{Style.RESET_ALL}")
        return
    
    try:
        print(f"{Fore.GREEN}🚀 Инициализация бота...{Style.RESET_ALL}")
        
        # Импортируем менеджер бота
        from core.bot_manager import BotManager
        
        # Создаем менеджер
        manager = BotManager()
        
        # Инициализируем бота
        if not await manager.initialize_bot():
            print(f"{Fore.RED}❌ Не удалось инициализировать бота{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}✅ Бот инициализирован{Style.RESET_ALL}")
        
        # Прямая загрузка модулей
        module_manager = await load_modules_directly(manager.client)
        
        if module_manager:
            # Устанавливаем владельца
            me = await manager.client.get_me()
            if hasattr(module_manager, 'owner_id'):
                module_manager.owner_id = me.id
            
            print(f"{Fore.GREEN}👤 Владелец: {me.first_name} (ID: {me.id}){Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🎉 Бот запущен и готов к работе!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Используйте {module_manager.prefix if hasattr(module_manager, 'prefix') else '.'}help для списка команд{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")
        
        # Запускаем клиент
        await manager.client.run_until_disconnected()
        
    except ImportError as e:
        print(f"{Fore.RED}❌ Ошибка импорта: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}📦 Попробуйте установить зависимости:{Style.RESET_ALL}")
        print(f"pip install -r requirements.txt")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🛑 Работа остановлена пользователем{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"\n{Fore.RED}💥 Критическая ошибка: {e}{Style.RESET_ALL}")
        traceback.print_exc()
    
    finally:
        print(f"\n{Fore.CYAN}👋 До свидания!{Style.RESET_ALL}")

if __name__ == '__main__':
    # Настройка цикла событий для Windows
    if sys.platform == 'win32':
        if sys.version_info >= (3, 8):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Запуск бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🛑 Программа остановлена{Style.RESET_ALL}")