import os
from typing import Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

SOURCE_FOLDER = 'source'
CONFIG_DIR = 'config'
os.makedirs(SOURCE_FOLDER, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'token.txt')
BOT_TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'bottoken.txt')
API_CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'api_credentials.txt')
ENV_FILE = os.path.join(CONFIG_DIR, '.env')

API_ID: str = ""
API_HASH: str = ""
BOT_TOKEN: Optional[str] = None

def get_api_credentials() -> Tuple[str, str]:
    """Получение API-данных с приоритетом: env → файл → ввод"""
    
    # 1. Проверяем переменные окружения
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    if api_id and api_hash:
        print("🔑 Используем API-данные из переменных окружения")
        return api_id, api_hash
    
    # 2. Проверяем файл .env в config
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    if line.startswith('API_ID='):
                        api_id = line.strip().split('=', 1)[1]
                    elif line.startswith('API_HASH='):
                        api_hash = line.strip().split('=', 1)[1]
            
            if api_id and api_hash:
                print("🔑 Используем API-данные из config/.env")
                return api_id, api_hash
        except Exception as e:
            print(f"⚠️ Ошибка чтения .env: {e}")
    
    # 3. Проверяем старые файлы
    file_checks = [
        (API_CREDENTIALS_FILE, "config/api_credentials.txt"),
        (TOKEN_FILE, "source/token.txt")
    ]
    
    for file_path, desc in file_checks:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if len(lines) >= 2:
                        print(f"🔑 Используем сохраненные API-данные из {desc}")
                        return lines[0], lines[1]
            except Exception as e:
                print(f"⚠️ Ошибка чтения {desc}: {e}")
    
    # 4. Запрашиваем у пользователя
    print("\n" + "="*50)
    print("🔐 Требуются данные Telegram API".center(50))
    print("Получите на my.telegram.org".center(50))
    print("="*50 + "\n")
    
    api_id = input("📝 Введите API ID: ").strip()
    api_hash = input("🔒 Введите API Hash: ").strip()

    if not (api_id and api_hash):
        raise ValueError("❌ API ID и Hash не могут быть пустыми")
    
    # Сохраняем в .env
    try:
        with open(ENV_FILE, 'w') as f:
            f.write(f"API_ID={api_id}\nAPI_HASH={api_hash}\n")
        print(f"✅ Данные сохранены в {ENV_FILE}")
    except Exception as e:
        print(f"⚠️ Не удалось сохранить в .env: {e}")
        # Резервное сохранение
        with open(API_CREDENTIALS_FILE, 'w') as f:
            f.write(f"{api_id}\n{api_hash}")
        print(f"✅ Данные сохранены в {API_CREDENTIALS_FILE}")
    
    return api_id, api_hash

def get_bot_token() -> Optional[str]:
    """Получение токена бота"""
    if os.path.exists(BOT_TOKEN_FILE):
        with open(BOT_TOKEN_FILE, 'r') as f:
            token_line = f.read().strip()
            if token_line:
                # Разные форматы токена
                if token_line.startswith('AAG') and len(token_line) >= 30:
                    return token_line
                elif ':' in token_line:
                    parts = token_line.split(':')
                    if len(parts) >= 4 and parts[3].startswith('AAG'):
                        return ':'.join(parts[2:])
                    elif len(parts) >= 3:
                        return ':'.join(parts[-2:])
    
    return None

API_ID, API_HASH = get_api_credentials()
