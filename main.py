import asyncio
import aiohttp
from telethon import TelegramClient, events
from config import API_ID, API_HASH
from modules import register_event_handlers, generate_username, run_bot
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_TOKEN_FILE = os.path.join(BASE_DIR, 'source', 'bottoken.txt')
BOT_IMAGE = os.path.join(BASE_DIR, 'source', 'pic.png')
# Добавьте в начало файла
PREFIX_FILE = os.path.join(BASE_DIR, 'source', 'prefix.txt')
DEFAULT_PREFIX = '.'


client = TelegramClient('acroka_user_session_{API_ID}', API_ID, API_HASH)

async def sleep(delay=1):
    """Задержка между сообщениями"""
    await asyncio.sleep(delay)

def get_prefix():
    """Получение текущего префикса команд"""
    if os.path.exists(PREFIX_FILE):
        with open(PREFIX_FILE, 'r') as f:
            prefix = f.read().strip()
            return prefix if len(prefix) == 1 else DEFAULT_PREFIX
    return DEFAULT_PREFIX

async def create_new_bot():
    """Создание нового бота через BotFather"""
    print("🛠️ Создание нового бота...")
    try:
        async with client.conversation('BotFather', exclusive=False) as conv:
            await conv.send_message('/newbot')
            await sleep()
            response = await conv.get_response()
            
            if "Alright" not in response.text:
                print("❌ Не удалось начать создание бота")
                return None, None, None

            await conv.send_message('Acroka Helper Bot')
            await sleep()
            await conv.get_response()

            username = generate_username()
            await conv.send_message(username)
            await sleep()
            response = await conv.get_response()

            if "Done!" not in response.text:
                print("❌ Не удалось создать бота")
                return None, None, None

            token_match = re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text)
            if not token_match:
                print("❌ Не удалось извлечь токен")
                return None, None, None

            token = token_match.group(1)
            user_id = token.split(':')[0]

            with open(BOT_TOKEN_FILE, 'w') as f:
                f.write(f"{username}:{user_id}:{token}")

            await set_bot_photo(username)
            
            print(f"✅ Бот @{username} успешно создан!")
            return username, user_id, token

    except Exception as e:
        print(f"❌ Ошибка при создании бота: {e}")
        return None, None, None

async def set_bot_photo(username):
    """Установка аватарки для бота"""
    if os.path.exists(BOT_IMAGE):
        try:
            async with client.conversation('BotFather', exclusive=True) as conv:
                await conv.send_message('/setuserpic')
                await sleep()
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await sleep()
                await conv.get_response()
                
                await conv.send_file(BOT_IMAGE)
                await sleep()
                await conv.get_response()
                print("🖼️ Аватарка бота установлена!")
        except Exception as e:
            print(f"⚠️ Не удалось установить аватарку: {e}")
    else:
        print(f"⚠️ Файл аватарки {BOT_IMAGE} не найден")

async def load_existing_bot(username):
    """Загрузка существующего бота"""
    print(f"🔍 Загрузка бота @{username}...")
    try:
        async with client.conversation('BotFather', exclusive=False) as conv:
            await conv.send_message('/token')
            await sleep()
            await conv.get_response()
            
            await conv.send_message(f'@{username}')
            await sleep()
            response = await conv.get_response()

            token_match = re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text)
            if not token_match:
                print("❌ Не удалось получить токен")
                return None, None

            token = token_match.group(1)
            user_id = token.split(':')[0]

            with open(BOT_TOKEN_FILE, 'w') as f:
                f.write(f"{username}:{user_id}:{token}")

            await set_bot_photo(username)
            
            print(f"✅ Бот @{username} успешно загружен!")
            return username, token

    except Exception as e:
        print(f"❌ Ошибка при загрузке бота: {e}")
        return None, None

async def check_bot_token(token):
    """Проверка валидности токена бота"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.telegram.org/bot{token}/getMe') as resp:
                data = await resp.json()
                return resp.status == 200 and data.get('ok', False)
    except Exception:
        return False

async def main():
    try:
        await client.start()
        print(f"🔑 Авторизован как: {(await client.get_me()).first_name}")

        if not os.path.exists(BOT_TOKEN_FILE) or os.stat(BOT_TOKEN_FILE).st_size == 0:
            choice = input("Файл токена пуст. Загрузить существующего бота? (да/нет): ").strip().lower()
            
            if choice == 'да':
                username = input("Введите юзернейм бота (без @): ").strip()
                result = await load_existing_bot(username)
                
                if not result:
                    print("🛑 Продолжение невозможно без токена бота")
                    return
                username, token = result
            else:
                result = await create_new_bot()
                if not result:
                    print("🛑 Продолжение невозможно без токена бота")
                    return
                username, user_id, token = result
        else:
            with open(BOT_TOKEN_FILE, 'r') as f:
                data = f.read().strip().split(':')
                if len(data) == 3:
                    username, user_id, token = data
                else:
                    print("❌ Неверный формат файла токена")
                    return

            if not await check_bot_token(token):
                print("❌ Недействительный токен бота")
                return

        register_event_handlers(client, get_prefix())
        bot_task = asyncio.create_task(run_bot(token))
        
        await client.send_message(f'@{username}', '/start')
        await bot_task

    except Exception as e:
        print(f"🛑 Критическая ошибка: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
