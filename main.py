import asyncio
import aiohttp
from telethon import TelegramClient
from config import API_ID, API_HASH
from modules import register_event_handlers, generate_username, run_bot
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_TOKEN_FILE = os.path.join(BASE_DIR, 'source', 'bottoken.txt')
BOT_IMAGE = os.path.join(BASE_DIR, 'source', 'pic.png')

client = TelegramClient('acroka_user_session', API_ID, API_HASH)

async def create_new_bot():
    """Создание нового бота через BotFather"""
    print("🛠️ Создание нового бота...")
    try:
        async with client.conversation('BotFather') as conv:
            # Шаг 1: Инициируем создание бота
            await conv.send_message('/newbot')
            response = await conv.get_response()
            
            if "Alright" not in response.text:
                print("❌ Не удалось начать создание бота")
                return None, None, None

            # Шаг 2: Отправляем имя бота
            await conv.send_message('Acroka Helper Bot')
            await conv.get_response()

            # Шаг 3: Отправляем юзернейм
            username = generate_username()
            await conv.send_message(username)
            response = await conv.get_response()

            if "Done!" not in response.text:
                print("❌ Не удалось создать бота")
                return None, None, None

            # Извлекаем токен
            token = None
            for line in response.text.split('\n'):
                if line.startswith('Use this token'):
                    token = line.split(':')[1].strip()
                    break

            if not token:
                print("❌ Не удалось извлечь токен")
                return None, None, None

            # Сохраняем данные бота
            user_id = token.split(':')[0]
            with open(BOT_TOKEN_FILE, 'w') as f:
                f.write(f"{username}:{user_id}:{token}")

            # Устанавливаем аватарку
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
            async with client.conversation('BotFather') as conv:
                await conv.send_message('/setuserpic')
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await conv.get_response()
                
                await conv.send_file(BOT_IMAGE)
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
        async with client.conversation('BotFather') as conv:
            # Запрашиваем токен
            await conv.send_message('/token')
            await conv.get_response()
            
            # Указываем юзернейм бота
            await conv.send_message(f'@{username}')
            response = await conv.get_response()

            if "You can use this token" not in response.text:
                print("❌ Не удалось получить токен")
                return None, None

            # Извлекаем токен
            token = response.text.split('token:')[1].strip().split()[0].replace("`", "")
            user_id = token.split(':')[0]

            # Сохраняем токен
            with open(BOT_TOKEN_FILE, 'w') as f:
                f.write(f"{username}:{user_id}:{token}")

            # Устанавливаем аватарку
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
                if resp.status == 200:
                    return True
        return False
    except Exception:
        return False

async def main():
    try:
        # Подключаемся к Telegram
        await client.start()
        print(f"🔑 Авторизован как: {(await client.get_me()).first_name}")

        # Проверяем наличие файла с токеном
        if not os.path.exists(BOT_TOKEN_FILE) or os.stat(BOT_TOKEN_FILE).st_size == 0:
            choice = input("Файл токена пуст. Загрузить существующего бота? (да/нет): ").strip().lower()
            
            if choice == 'да':
                username = input("Введите юзернейм бота (без @): ").strip()
                username, token = await load_existing_bot(username)
                
                if not token:
                    print("🛑 Продолжение невозможно без токена бота")
                    return
            else:
                username, user_id, token = await create_new_bot()
                if not token:
                    print("🛑 Продолжение невозможно без токена бота")
                    return
        else:
            # Читаем существующий токен
            with open(BOT_TOKEN_FILE, 'r') as f:
                data = f.read().strip().split(':')
                if len(data) == 3:
                    username, user_id, token = data
                else:
                    print("❌ Неверный формат файла токена")
                    return

            # Проверяем токен
            if not await check_bot_token(token):
                print("❌ Недействительный токен бота")
                return

        # Регистрируем обработчики команд
        register_event_handlers(client)
        
        # Запускаем бота
        bot_task = asyncio.create_task(run_bot(client, token))
        
        # Отправляем тестовое сообщение
        await client.send_message(f'@{username}', '/start')
        
        # Ожидаем завершения
        await bot_task

    except Exception as e:
        print(f"🛑 Критическая ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())