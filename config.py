import os
from typing import Tuple, Optional

# Пути к файлам конфигурации
SOURCE_FOLDER = 'source'
CONFIG_DIR = 'config'
os.makedirs(SOURCE_FOLDER, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# Файлы конфигурации
TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'token.txt')
BOT_TOKEN_FILE = os.path.join(CONFIG_DIR, 'bot_token.txt')
API_CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'api_credentials.txt')

# Глобальные переменные для хранения конфигурации
API_ID: str = ""
API_HASH: str = ""
BOT_TOKEN: Optional[str] = None

def get_api_credentials() -> Tuple[str, str]:
    if os.path.exists(API_CREDENTIALS_FILE):
        try:
            with open(API_CREDENTIALS_FILE) as f:
                credentials = [line.strip() for line in f if line.strip()]
                if len(credentials) >= 2:
                    print("🔑 Используем сохраненные API-данные из config/api_credentials.txt")
                    return tuple(credentials[:2])
        except Exception as e:
            print(f"⚠️ Ошибка чтения API-данных: {e}")

    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                lines = f.read().strip().split('\n')
                if len(lines) >= 2:
                    print("🔑 Используем сохраненные API-данные из source/token.txt")
                    return lines[0], lines[1]
        except Exception as e:
            print(f"⚠️ Ошибка чтения API-данных: {e}")

    print("\n🔐 Требуются данные Telegram API (получить на my.telegram.org)")
    api_id = input("📝 Введите API ID: ").strip()
    api_hash = input("🔒 Введите API Hash: ").strip()

    if not (api_id and api_hash):
        raise ValueError("❌ API ID и Hash не могут быть пустыми")

    with open(API_CREDENTIALS_FILE, 'w') as f:
        f.write(f"{api_id}\n{api_hash}")
    
    print(f"✅ Данные успешно сохранены в {API_CREDENTIALS_FILE}")
    return api_id, api_hash

def get_bot_token() -> Optional[str]:
    if os.path.exists(BOT_TOKEN_FILE):
        with open(BOT_TOKEN_FILE, 'r') as f:
            token_line = f.read().strip()
            if token_line:
                if token_line.startswith('AAG') and len(token_line) >= 30:
                    return token_line
                elif ':' in token_line:
                    parts = token_line.split(':')
                    if len(parts) >= 4 and parts[3].startswith('AAG'):
                        return ':'.join(parts[2:])
    
    old_token_file = os.path.join(SOURCE_FOLDER, 'bottoken.txt')
    if os.path.exists(old_token_file):
        with open(old_token_file, 'r') as f:
            token_line = f.read().strip()
            if token_line:
                if token_line.startswith('AAG') and len(token_line) >= 30:
                    return token_line

# Вызов функции для получения API ID и API Hash
API_ID, API_HASH = get_api_credentials()
