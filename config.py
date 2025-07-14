import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict

class TelegramConfig:
    def __init__(self):
        self.BASE_DIR = Path(__file__).parent
        self.CONFIG_FILE = self.BASE_DIR / 'config' / 'telegram_config.json'
        self.BOT_TOKEN_FILE = self.BASE_DIR / 'config' / 'bot_token.txt'
        
        # Создаем папку config если не существует
        self.CONFIG_FILE.parent.mkdir(exist_ok=True)
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Проверяем обязательные параметры
        if not self._validate_credentials():
            self._setup_credentials()

    def _load_config(self) -> Dict:
        """Загрузка конфигурации из файла"""
        default_config = {
            'api_id': '',
            'api_hash': '',
            'session_name': 'default_session'
        }
        
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Ошибка чтения конфига: {e}", file=sys.stderr)
        
        return default_config

    def _save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️ Ошибка сохранения конфига: {e}", file=sys.stderr)

    def _validate_credentials(self) -> bool:
        """Проверка валидности учетных данных"""
        api_id = self.config.get('api_id', '')
        api_hash = self.config.get('api_hash', '')
        return bool(api_id and api_hash and str(api_id).isdigit() and len(api_hash) >= 10)

    def _setup_credentials(self):
        """Настройка учетных данных"""
        print("\n🔐 Требуется настройка Telegram API", file=sys.stderr)
        print("1. Получите API ID и Hash на https://my.telegram.org", file=sys.stderr)
        print("2. Создайте приложение в разделе 'API development tools'\n", file=sys.stderr)
        
        try:
            self.config['api_id'] = input("Введите API ID: ").strip()
            self.config['api_hash'] = input("Введите API Hash: ").strip()
            
            if not self._validate_credentials():
                print("❌ Неверные учетные данные", file=sys.stderr)
                sys.exit(1)
                
            self._save_config()
            print("✅ Настройки сохранены", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Настройка прервана", file=sys.stderr)
            sys.exit(1)

    def _load_bot_token(self) -> Optional[str]:
        """Загрузка токена бота из файла"""
        if not self.BOT_TOKEN_FILE.exists():
            return None
            
        try:
            with open(self.BOT_TOKEN_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.count(':') >= 2:
                    parts = content.split(':')
                    if len(parts[3]) >= 30 and parts[3].startswith('AAG'):
                        return ':'.join(parts[2:])
        except Exception as e:
            print(f"⚠️ Ошибка чтения токена: {e}", file=sys.stderr)
        
        return None

    @property
    def api_id(self) -> str:
        return str(self.config['api_id'])

    @property
    def api_hash(self) -> str:
        return self.config['api_hash']

    @property
    def bot_token(self) -> Optional[str]:
        return self._load_bot_token()


# Инициализация конфигурации
try:
    tg_config = TelegramConfig()
    
    # Экспорт для совместимости
    API_ID = tg_config.api_id
    API_HASH = tg_config.api_hash
    BOT_TOKEN = tg_config.bot_token
    
    # Проверка обязательных параметров
    if not API_ID or not API_HASH:
        raise ValueError("API ID и Hash обязательны для работы")

except Exception as e:
    print(f"🛑 Фатальная ошибка: {str(e)}", file=sys.stderr)
    sys.exit(1)
