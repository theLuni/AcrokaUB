import os
import sys
import json
from pathlib import Path
from typing import Optional, Tuple, Dict

class ConfigManager:
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent
        self.CONFIG_DIR = self.BASE_DIR / 'config'
        self.CONFIG_DIR.mkdir(exist_ok=True)
        
        self.CONFIG_FILE = self.CONFIG_DIR / 'settings.json'
        self.BOT_TOKEN_FILE = self.CONFIG_DIR / 'bot_token.txt'
        
        self.settings = self._load_settings()
        self.API_ID = self.settings.get('api_id')
        self.API_HASH = self.settings.get('api_hash')
        self.BOT_TOKEN = self._load_bot_token()

    def _load_settings(self) -> Dict:
        """Загрузка настроек из JSON файла"""
        default_settings = {
            'api_id': '',
            'api_hash': '',
            'session_name': 'default_session'
        }
        
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if all(k in loaded for k in ['api_id', 'api_hash']):
                        return loaded
            except (json.JSONDecodeError, IOError):
                pass
        
        return default_settings

    def _save_settings(self):
        """Сохранение настроек в JSON файл"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️ Ошибка сохранения настроек: {e}", file=sys.stderr)

    def _load_bot_token(self) -> Optional[str]:
        """Загрузка токена бота из файла"""
        if not self.BOT_TOKEN_FILE.exists():
            return None
            
        try:
            with open(self.BOT_TOKEN_FILE, 'r', encoding='utf-8') as f:
                token_line = f.read().strip()
                parts = token_line.split(':')
                
                if len(parts) >= 4 and len(parts[3]) >= 30 and parts[3].startswith('AAG'):
                    return ':'.join(parts[2:])
        except Exception:
            return None
            
        return None

    def _input_credentials(self):
        """Красивый ввод учетных данных"""
        from getpass import getpass
        
        print("\n" + "="*40)
        print("🔐 Настройка авторизации Telegram".center(40))
        print("="*40 + "\n")
        
        print("1. Получить API ID и Hash:")
        print("   - Перейдите на https://my.telegram.org")
        print("   - Создайте приложение в разделе 'API development tools'\n")
        
        try:
            self.settings['api_id'] = input("Введите API ID: ").strip()
            self.settings['api_hash'] = getpass("Введите API Hash: ").strip()
            
            print("\n" + "="*40)
            print("🚀 Настройки сохранены!".center(40))
            print("="*40 + "\n")
            
            self._save_settings()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️ Ввод прерван. Настройки не сохранены.", file=sys.stderr)
            sys.exit(1)

    def _menu_interactive(self):
        """Интерактивное меню настройки"""
        while True:
            print("\nМеню настройки авторизации:")
            print("1. Ввести API ID и Hash вручную")
            print("2. Загрузить из файла конфигурации")
            print("3. Проверить текущие настройки")
            print("4. Выход")
            
            try:
                choice = input("Выберите действие (1-4): ").strip()
                
                if choice == '1':
                    self._input_credentials()
                    return
                elif choice == '2':
                    if self.CONFIG_FILE.exists():
                        self.settings = self._load_settings()
                        print("✅ Настройки загружены из файла")
                        return
                    print("⚠️ Файл конфигурации не найден", file=sys.stderr)
                elif choice == '3':
                    self._show_current_settings()
                elif choice == '4':
                    sys.exit("Настройка отменена")
                else:
                    print("⚠️ Неверный выбор, попробуйте снова", file=sys.stderr)
            except (EOFError, KeyboardInterrupt):
                print("\n⚠️ Ввод прерван.", file=sys.stderr)
                sys.exit(1)

    def _show_current_settings(self):
        """Показать текущие настройки"""
        print("\nТекущие настройки:")
        print(f"API ID: {'установлен' if self.settings.get('api_id') else 'не установлен'}")
        print(f"API Hash: {'установлен' if self.settings.get('api_hash') else 'не установлен'}")
        print(f"Токен бота: {'установлен' if self.BOT_TOKEN else 'не установлен'}")

    def setup(self):
        """Основной метод настройки"""
        if not self.settings.get('api_id') or not self.settings.get('api_hash'):
            try:
                # Проверяем, есть ли интерактивный терминал
                if sys.stdin.isatty():
                    self._menu_interactive()
                else:
                    raise RuntimeError("Нет интерактивного терминала для ввода")
            except Exception as e:
                print(f"⚠️ Ошибка настройки: {e}", file=sys.stderr)
                sys.exit(1)
        
        # Проверяем валидность настроек
        if not str(self.settings['api_id']).isdigit() or len(self.settings['api_hash']) < 10:
            print("\n⚠️ Неверный формат API ID/Hash.", file=sys.stderr)
            sys.exit(1)


# Инициализация конфигурации
try:
    config = ConfigManager()
    
    # Автоматическая проверка только если есть интерактивный терминал
    if sys.stdin.isatty() and (not config.API_ID or not config.API_HASH):
        config.setup()

    API_ID = config.API_ID
    API_HASH = config.API_HASH
    BOT_TOKEN = config.BOT_TOKEN

except Exception as e:
    print(f"⚠️ Ошибка инициализации конфигурации: {e}", file=sys.stderr)
    sys.exit(1)
