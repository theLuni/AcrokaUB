import os

# Путь к папке source
SOURCE_FOLDER = 'source'
if not os.path.exists(SOURCE_FOLDER):
    os.makedirs(SOURCE_FOLDER)

# Файл для хранения токена и информации о пользователе
TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'token.txt')

def get_api_credentials():
    """Функция для получения API ID и API Hash из файла или запрос у пользователя."""
    
    # Проверяем, существует ли файл с токеном
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            lines = f.read().strip().split('\n')
            print("Содержимое файла:", lines)  # Для отладки
            
            # Проверяем, что файл содержит как минимум 2 строки
            if len(lines) >= 2:
                api_id = lines[0]
                api_hash = lines[1]
                print("✅ Токен успешно загружен из файла.")
                return api_id, api_hash
            else:
                print("❌ Ошибка: Неверный формат файла с токеном. Ожидалось 2 строки, будет запрошен ввод данных.")
    
    # Если файл отсутствует или содержит некорректные данные, запрашиваем у пользователя
    print("Файл с токеном не найден или имеет некорректный формат.")
    api_id = input("Введите ваш API ID: ")
    api_hash = input("Введите ваш API Hash: ")

    # Сохраняем полученные данные в файл
    with open(TOKEN_FILE, 'w') as f:
        f.write(f"{api_id}\n{api_hash}")
        print("✅ Токен успешно сохранен в файл.")
    
    return api_id, api_hash

import os

def get_bot_token():
    """
    Получает токен бота из файла /source/bottoken.txt в формате:
    'hasaco_bot:7728200289:7728200289:AAG3NA0ZWgBPKkJjkGYCxZtCjCrX5fEJxj8'
    
    Возвращает:
        str: Токен бота (часть после второго двоеточия) или None, если файл пустой/некорректный
    
    Исключения:
        FileNotFoundError: Если файл не существует
    """
    token_file = os.path.join('source', 'bottoken.txt')
    
    if not os.path.exists(token_file):
        raise FileNotFoundError(f"Файл с токеном не найден: {token_file}")
    
    with open(token_file, 'r') as f:
        token_line = f.read().strip()
    
    # Если файл пустой - возвращаем None
    if not token_line:
        return None
        
    try:
        # Разделяем строку по двоеточиям
        parts = token_line.split(':')
        
        # Проверяем минимальную длину и наличие токена
        if len(parts) < 4:
            return None
            
        # Проверяем, что последняя часть похожа на токен (длина и начало)
        token_part = parts[3]
        if len(token_part) < 30 or not token_part.startswith('AAG'):
            return None
            
        return ':'.join(parts[2:])  # Возвращаем все после второго двоеточия
        
    except Exception as e:
        # Ловим любые ошибки парсинга и возвращаем None
        return None
        
BOT_TOKEN = get_bot_token()

# Вызов функции получения API ID и API Hash
API_ID, API_HASH = get_api_credentials()
