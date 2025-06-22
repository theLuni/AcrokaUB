import os

# Путь к папке source
SOURCE_FOLDER = 'source'
if not os.path.exists(SOURCE_FOLDER):
    os.makedirs(SOURCE_FOLDER)

# Файл для хранения токена и информации о пользователе
TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'token.txt')

def get_api_credentials():
    # Проверяем, существует ли файл с токеном
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            api_id, api_hash = f.read().strip().split('\n')
    else:
        # Запрашиваем данные у пользователя
        api_id = input("Введите ваш API ID: ")
        api_hash = input("Введите ваш API Hash: ")

        # Сохраняем данные в файл
        with open(TOKEN_FILE, 'w') as f:
            f.write(f"{api_id}\n{api_hash}")
    
    return api_id, api_hash

API_ID, API_HASH = get_api_credentials()
