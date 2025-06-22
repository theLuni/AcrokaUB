import os
import asyncio
from telethon import TelegramClient
from config import API_ID, API_HASH, TOKEN_FILE
from modules import register_event_handlers, create_bot, run_bot
from datetime import datetime

client = TelegramClient('userbot', API_ID, API_HASH)

# Записываем время запуска
start_time = datetime.now()  # Инициализация переменной start_time

async def main():
    try:
        await client.start()

        if not os.path.exists(TOKEN_FILE) or os.stat(TOKEN_FILE).st_size == 0:
            username, user_id, token = await create_bot(client)
            if token:
                await asyncio.sleep(5)
            else:
                return
        else:
            with open(TOKEN_FILE, 'r') as f:
                data = f.read().strip()
                username, user_id, token = data.split(':', 2)

        register_event_handlers(client)
        bot_running = asyncio.create_task(run_bot(client, token))

        # Задержка перед отправкой сообщения команды /start
        await asyncio.sleep(10)
        await client.send_message(f'@{username}', '/start')

        await bot_running  

    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(main())