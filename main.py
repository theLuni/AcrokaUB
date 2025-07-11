import asyncio
import aiohttp
from telethon import TelegramClient
from config import API_ID, API_HASH
from modules import register_event_handlers, generate_username, run_bot
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_TOKEN_FILE = os.path.join(BASE_DIR, 'source', 'bottoken.txt')
BOT_IMAGE = os.path.join(BASE_DIR, 'source', 'pic.png')

client = TelegramClient('acroka_user_session', API_ID, API_HASH)

async def sleep(delay=1):
    """Задержка между сообщениями"""
    await asyncio.sleep(delay)

async def create_new_bot():
    """Создание нового бота через BotFather"""
    print("🛠️ Создание нового бота...")
    try:
        async with client.conversation('BotFather') as conv:
            # Шаг 1: Инициируем создание бота
            await conv.send_message('/newbot')
            await sleep()
            response = await conv.get_response()
            
            if "Alright" not in response.text:
                print("❌ Не удалось начать создание бота")
                print(f"Ответ BotFather: {response.text}")
                return None, None, None

            # Шаг 2: Отправляем имя бота
            await conv.send_message('Acroka Helper Bot')
            await sleep()
            await conv.get_response()

            # Шаг 3: Отправляем юзернейм
            username = generate_username()
            await conv.send_message(username)
            await sleep()
            response = await conv.get_response()

            if "Done!" not in response.text:
                print("❌ Не удалось создать бота")
                print(f"Ответ BotFather: {response.text}")
                return None, None, None

            # Извлекаем токен из ответа
            token = None
            # Вариант 1: Токен на отдельной строке после "Use this token"
            if "Use this token" in response.text:
                token_match = re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text)
                if token_match:
                    token = token_match.group(1)
                else:
                    # Если токен в следующем сообщении
                    await sleep()
                    token_msg = await conv.get_response()
                    token_match = re.search(r'(\d+:[a-zA-Z0-9_-]+)', token_msg.text)
                    if token_match:
                        token = token_match.group(1)
            
            # Вариант 2: Просто ищем строку с форматом токена
            if not token:
                for line in response.text.split('\n'):
                    if re.match(r'^\d+:[a-zA-Z0-9_-]+$', line.strip()):
                        token = line.strip()
                        break

            if not token:
                print("❌ Не удалось извлечь токен")
                print(f"Ответ BotFather: {response.text}")
                return None, None, None

            # Очищаем токен от лишних символов
            token = re.sub(r'[`"\']', '', token).strip()
            user_id = token.split(':')[0]

            # Сохраняем данные бота
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
        async with client.conversation('BotFather') as conv:
            # Запрашиваем токен
            await conv.send_message('/token')
            await sleep()
            await conv.get_response()
            
            # Указываем юзернейм бота
            await conv.send_message(f'@{username}')
            await sleep()
            response = await conv.get_response()

            # Ищем токен в ответе
            token = None
            # Вариант 1: Токен на отдельной строке после "You can use this token"
            if "You can use this token" in response.text:
                token_match = re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text)
                if token_match:
                    token = token_match.group(1)
                else:
                    # Если токен в следующем сообщении
                    await sleep()
                    token_msg = await conv.get_response()
                    token_match = re.search(r'(\d+:[a-zA-Z0-9_-]+)', token_msg.text)
                    if token_match:
                        token = token_match.group(1)
            
            # Вариант 2: Просто ищем строку с форматом токена
            if not token:
                for line in response.text.split('\n'):
                    if re.match(r'^\d+:[a-zA-Z0-9_-]+$', line.strip()):
                        token = line.strip()
                        break

            if not token:
                print("❌ Не удалось получить токен")
                print(f"Ответ BotFather: {response.text}")
                return None, None

            # Очищаем токен от лишних символов
            token = re.sub(r'[`"\']', '', token).strip()
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
                data = await resp.json()
                return resp.status == 200 and data.get('ok', False)
    except Exception as e:
        print(f"⚠️ Ошибка проверки токена: {e}")
        return False

async def main():
    try:
        # Подключаемся к Telegram
        await client.start()
        me = await client.get_me()
        print(f"🔑 Авторизован как: {me.first_name}")

        # Проверяем наличие файла с токеном
        if not os.path.exists(BOT_TOKEN_FILE) or os.stat(BOT_TOKEN_FILE).st_size == 0:
            choice = input("Файл токена пуст. Загрузить существующего бота? (да/нет): ").strip().lower()
            
            if choice == 'да':
                username = input("Введите юзернейм бота (без @): ").strip()
                result = await load_existing_bot(username)
                
                if not result or len(result) != 2:
                    print("🛑 Продолжение невозможно без токена бота")
                    return
                username, token = result
            else:
                result = await create_new_bot()
                if not result or len(result) != 3:
                    print("🛑 Продолжение невозможно без токена бота")
                    return
                username, user_id, token = result
        else:
            # Читаем существующий токен
            try:
                with open(BOT_TOKEN_FILE, 'r') as f:
                    data = f.read().strip().split(':')
                    if len(data) == 3:
                        username, user_id, token = data
                    else:
                        print("❌ Неверный формат файла токена (ожидается username:user_id:token)")
                        return

                # Проверяем токен
                if not await check_bot_token(token):
                    print("❌ Недействительный токен бота")
                    return
            except Exception as e:
                print(f"❌ Ошибка чтения файла токена: {e}")
                return

        # Регистрируем обработчики команд для основного клиента
        register_event_handlers(client)
        
        # Запускаем бота
        bot_task = asyncio.create_task(run_bot(token))
        
        # Отправляем тестовое сообщение
        try:
            await client.send_message(f'@{username}', '/start')
        except Exception as e:
            print(f"⚠️ Не удалось отправить тестовое сообщение: {e}")
        
        # Ожидаем завершения
        await bot_task

    except Exception as e:
        print(f"🛑 Критическая ошибка: {e}")
    finally:
        if client.is_connected():  # Убрали await, так как is_connected() не корутина
            await client.disconnect()
            
if __name__ == '__main__':
    asyncio.run(main())
