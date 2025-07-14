import os

# Константы
SOURCE_FOLDER = 'source'
TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'token.txt')
BOT_TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'bottoken.txt')

# Создаем папку source, если ее нет
os.makedirs(SOURCE_FOLDER, exist_ok=True)

def get_api_credentials():
    """Получает API ID и API Hash из файла или запрашивает у пользователя."""
    try:
        # Пытаемся прочитать из файла
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                
                if len(lines) >= 2:
                    return lines[0], lines[1]
    except Exception:
        pass  # В случае ошибки просто запросим данные заново
    
    # Если файла нет или данные некорректны, запрашиваем у пользователя
    try:
        api_id = input("Введите ваш API ID: ").strip()
        api_hash = input("Введите ваш API Hash: ").strip()
        
        # Сохраняем в файл
        with open(TOKEN_FILE, 'w') as f:
            f.write(f"{api_id}\n{api_hash}")
            
        return api_id, api_hash
    except EOFError:
        raise RuntimeError("Не удалось получить данные для входа. Проверьте правильность ввода.")

def get_bot_token():
    """Получает токен бота из файла."""
    if not os.path.exists(BOT_TOKEN_FILE):
        raise FileNotFoundError(f"Файл с токеном бота не найден: {BOT_TOKEN_FILE}")
    
    with open(BOT_TOKEN_FILE, 'r') as f:
        token_line = f.read().strip()
    
    if not token_line:
        return None
        
    try:
        parts = token_line.split(':')
        if len(parts) >= 4 and len(parts[3]) >= 30 and parts[3].startswith('AAG'):
            return ':'.join(parts[2:])
    except Exception:
        pass
        
    return None

# Инициализация констант
try:
    BOT_TOKEN = get_bot_token()
    API_ID, API_HASH = get_api_credentials()
except Exception as e:
    print(f"Ошибка инициализации: {str(e)}")
    raise
