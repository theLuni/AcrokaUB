
import asyncio
import aiohttp  # Не забудьте установить aiohttp, если еще этого не сделали
from telethon import TelegramClient
from config import API_ID, API_HASH
from modules import register_event_handlers, generate_username, run_bot
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущей директории
BOT_TOKEN = os.path.join(BASE_DIR, 'source', 'bottoken.txt')  # Путь к файлу с токеном

client = TelegramClient('userbot', API_ID, API_HASH)

async def create_bot(client):
    botfather = await client.get_input_entity('BotFather')
    bot_title = 'Acroka'

    try:
        await client.send_message(botfather, '/newbot')
        await asyncio.sleep(2)
        await client.send_message(botfather, bot_title)
        await asyncio.sleep(2)

        username = generate_username()
        await client.send_message(botfather, username)
        await asyncio.sleep(5)

        token = None
        async for message in client.iter_messages(botfather, limit=10):
            if 'Use this token to access the HTTP API:' in message.message:
                lines = message.message.split('\n')
                for i, line in enumerate(lines):
                    if 'Use this token to access the HTTP API:' in line and i + 1 < len(lines):
                        token = lines[i + 1].strip()
                        break
                if token:
                    break
        else:
            print("Не удалось получить токен от BotFather.")
            return None, None

        user_id = token.split(':')[0]
        with open(BOT_TOKEN, 'w') as f:
            f.write(f"{username}:{user_id}:{token}")

        # Отправка команд, чтобы настроить бота
        await client.send_message(botfather, '/setuserpic')
        await asyncio.sleep(2)
        await client.send_message(botfather, f'@{username}')
        await asyncio.sleep(2)

        # Путь к изображению
        photo_path = os.path.abspath('source/pic.png')
        if os.path.exists(photo_path):
            await client.send_file(botfather, photo_path)
        else:
            print(f"Ошибка: Файл '{photo_path}' не существует.")

        return username, user_id, token
    
    except Exception as e:
        print(f"Ошибка при создании бота: {e}")
        return None, None

async def check_token(token):
    url = f'https://api.telegram.org/bot{token}/getMe'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Ошибка проверки токена: {response.status}")
                return None

async def get_token(username):
    botfather_username = '@BotFather'
    
    # Запрашиваем токен у BotFather
    await client.send_message(botfather_username, '/token')  # Запрос токена
    await asyncio.sleep(2)  # Ожидание для получения ответа
    await client.send_message(botfather_username, f'@{username}')  # Указание юзернейма
    await asyncio.sleep(2)  # Ожидание для получения ответа
    
    async for message in client.iter_messages(botfather_username, limit=10):
        if "You can use this token to access HTTP API:" in message.text:
            token_line = message.text.split("You can use this token to access HTTP API:")[1].strip()
            token = token_line.split()[0].replace("`", "").strip()  # Убираем обратные кавычки и пробелы
            
            # Устанавливаем пользовательское фото
            await client.send_message(botfather_username, '/setuserpic')
            await asyncio.sleep(2)
            await client.send_message(botfather_username, f'@{username}')  # Отправляем юзернейм
            await asyncio.sleep(2)

            # Путь к изображению
            photo_path = os.path.abspath('source/pic.png')
            if os.path.exists(photo_path):
                await client.send_file(botfather_username, photo_path)  # Отправляем фото BotFather
            else:
                print(f"Ошибка: Файл '{photo_path}' не существует.")
                
            return username, token  # Возвращаем юзернейм и токен

    return None
async def main():
    try:
        await client.start()

        if not os.path.exists(BOT_TOKEN) or os.stat(BOT_TOKEN).st_size == 0:
            load_existing = input("Файл токена пуст. Хотите загрузить существующего бота? (да/нет): ").strip().lower()
            if load_existing == 'да':
                username = input("Введите юзернейм вашего бота (без @): ").strip()
                token_data = await get_token(username)  # Получение токена

                if token_data:  # Проверьте, существует ли token_data
                    user_id = token_data.split(":")[0]
                    data_to_save = f'{username}:{user_id}:{token_data}'
                    with open(BOT_TOKEN, 'w') as f:
                        f.write(data_to_save.strip())
                else:
                    print("Не удалось получить токен от @BotFather.")
                    return
            else:
                print("Создаем нового бота...")
                username, user_id, token = await create_bot(client)  # Создание нового бота

        if os.path.exists(BOT_TOKEN) and os.stat(BOT_TOKEN).st_size > 0:
            with open(BOT_TOKEN, 'r') as f:
                data = f.read().strip()
                username, user_id, token = data.split(':', 2)

            register_event_handlers(client)
            bot_running = asyncio.create_task(run_bot(client, token))

            await asyncio.sleep(10)
            await client.send_message(f'@{username}', '/start')

            await bot_running  
        else:
            print("Ошибка: файл токена не создан.")

    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(main())
