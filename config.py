import os

# Путь к папке source
SOURCE_FOLDER = 'source'
if not os.path.exists(SOURCE_FOLDER):
    os.makedirs(SOURCE_FOLDER)

# Файл для хранения токена и информации о пользователе
TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'token.txt')

def get_api_credentials():
    """Функция для получения API ID и API Hash из файла или запроса у пользователя."""
    
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
                print("❌ Ошибка: Неверный формат файла с токеном. Ожидалось 2 строки.")
    
    # Если файл отсутствует или содержит некорректные данные, запрашиваем у пользователя
    print("Файл с токеном не найден или имеет некорректный формат.")
    api_id = input("Введите ваш API ID: ")
    api_hash = input("Введите ваш API Hash: ")

    # Сохраняем полученные данные в файл
    with open(TOKEN_FILE, 'w') as f:
        f.write(f"{api_id}\n{api_hash}")
        print("✅ Токен успешно сохранен в файл.")
    
    return api_id, api_hash

# Вызов функции получения API ID и API Hash
API_ID, API_HASH = get_api_credentials()
