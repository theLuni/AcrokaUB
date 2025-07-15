import os
from typing import Tuple, Optional

# 📂 Константы
CONFIG_DIR = 'config'
API_CREDENTIALS_FILE = os.path.join(CONFIG_DIR, 'api_credentials.txt')
BOT_TOKEN_FILE = os.path.join(CONFIG_DIR, 'bot_token.txt')

# 🔄 Создаем папку config, если ее нет
os.makedirs(CONFIG_DIR, exist_ok=True)


def get_api_credentials() -> Tuple[str, str]:
    """
    🔑 Получает API ID и API Hash из файла или запрашивает у пользователя.
    
    Возвращает:
        Tuple[str, str]: Кортеж (API_ID, API_HASH)
        
    Вызывает:
        ValueError: Если данные неверные или отсутствуют
    """
    if os.path.exists(API_CREDENTIALS_FILE):
        try:
            with open(API_CREDENTIALS_FILE) as f:
                credentials = [line.strip() for line in f if line.strip()]
                if len(credentials) >= 2:
                    print("🔑 Используем сохраненные API-данные")
                    return tuple(credentials[:2])
        except Exception as e:
            print(f"⚠️ Ошибка чтения API-данных: {e}")

    print("\n🔐 Требуются данные Telegram API (получить на my.telegram.org)")
    api_id = input("📝 Введите API ID: ").strip()
    api_hash = input("🔒 Введите API Hash: ").strip()

    if not (api_id and api_hash):
        raise ValueError("❌ API ID и Hash не могут быть пустыми")

    with open(API_CREDENTIALS_FILE, 'w') as f:
        f.write(f"{api_id}\n{api_hash}")
    
    print("✅ Данные успешно сохранены")
    return api_id, api_hash


def get_bot_token() -> Optional[str]:
    """
    🤖 Получает токен бота из файла.
    
    Возвращает:
        Optional[str]: Токен бота или None, если токен невалидный
    """
    if not os.path.exists(BOT_TOKEN_FILE):
        print("⚠️ Файл с токеном бота не найден")
        return None

    with open(BOT_TOKEN_FILE) as f:
        token = f.read().strip()

    if not token:
        print("⚠️ Файл с токеном бота пуст")
        return None

    if ':' not in token or len(token.split(':')[1]) < 30:
        print("❌ Неверный формат токена бота")
        return None

    print("🔑 Токен бота успешно загружен")
    return token


def initialize_config() -> None:
    """⚙️ Инициализирует конфигурационные параметры."""
    global BOT_TOKEN, API_ID, API_HASH
    
    try:
        BOT_TOKEN = get_bot_token()
        API_ID, API_HASH = get_api_credentials()
        print("\n🎉 Конфигурация успешно загружена!")
    except Exception as e:
        print(f"\n❌ Ошибка инициализации: {e}")
        print("Пожалуйста, проверьте конфигурационные файлы")
        raise


# 🚀 Запуск инициализации
if __name__ == '__main__':
    initialize_config()
