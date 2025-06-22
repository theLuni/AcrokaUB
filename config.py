import os
from telethon import TelegramClient

API_ID = '24755102'  # Замените на ваш API_ID
API_HASH = 'fb23dc1caeb3349abb5e0ebcdafc0bcf'  # Замените на ваш API_HASH

# Путь к папке source
SOURCE_FOLDER = 'source'
if not os.path.exists(SOURCE_FOLDER):
    os.makedirs(SOURCE_FOLDER)

# Файлы для хранения токена и информации о пользователе
TOKEN_FILE = os.path.join(SOURCE_FOLDER, 'bottoken.txt')
INFO_FILE = os.path.join(SOURCE_FOLDER, 'userinfo.txt')