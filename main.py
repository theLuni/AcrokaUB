import asyncio
import os
import re
import aiohttp
from telethon import TelegramClient, events
from config import API_ID, API_HASH

class BotManager:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.BOT_TOKEN_FILE = os.path.join(self.BASE_DIR, 'source', 'bottoken.txt')
        self.BOT_IMAGE = os.path.join(self.BASE_DIR, 'source', 'pic.png')
        self.PREFIX_FILE = os.path.join(self.BASE_DIR, 'source', 'prefix.txt')
        self.DEFAULT_PREFIX = '.'
        self.client = TelegramClient(f'acroka_session_{API_ID}', API_ID, API_HASH)

    async def sleep(self, delay=1):
        await asyncio.sleep(delay)

    def get_prefix(self):
        if os.path.exists(self.PREFIX_FILE):
            with open(self.PREFIX_FILE, 'r') as f:
                prefix = f.read().strip()
                return prefix if len(prefix) == 1 else self.DEFAULT_PREFIX
        return self.DEFAULT_PREFIX

    async def create_new_bot(self):
        """Создание нового бота через BotFather"""
        print("🛠️ Создание нового бота...")
        try:
            async with self.client.conversation('BotFather') as conv:
                await conv.send_message('/newbot')
                await self.sleep()
                
                response = await conv.get_response()
                if "Alright" not in response.text:
                    print("❌ Не удалось начать создание бота")
                    return None, None, None

                await conv.send_message('Acroka Helper Bot')
                await self.sleep()
                await conv.get_response()

                username = self.generate_username()
                await conv.send_message(username)
                await self.sleep()
                response = await conv.get_response()

                if "Done!" not in response.text:
                    print("❌ Не удалось создать бота")
                    return None, None, None

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    with open(self.BOT_TOKEN_FILE, 'w') as f:
                        f.write(f"{username}:{user_id}:{token}")

                    await self.set_bot_photo(username)
                    print(f"✅ Бот @{username} успешно создан!")
                    return username, user_id, token

        except Exception as e:
            print(f"❌ Ошибка при создании бота: {e}")
        return None, None, None

    def generate_username(self):
        """Генерация уникального имени бота"""
        import random
        import string
        chars = string.ascii_lowercase + string.digits
        rand_part = ''.join(random.choice(chars) for _ in range(6)
        return f'acroka_{rand_part}_bot'

    async def set_bot_photo(self, username):
        """Установка аватарки для бота"""
        if not os.path.exists(self.BOT_IMAGE):
            print(f"⚠️ Файл аватарки {self.BOT_IMAGE} не найден")
            return

        try:
            async with self.client.conversation('BotFather') as conv:
                await conv.send_message('/setuserpic')
                await self.sleep()
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await self.sleep()
                await conv.get_response()
                
                await conv.send_file(self.BOT_IMAGE)
                await self.sleep()
                await conv.get_response()
                print("🖼️ Аватарка бота установлена!")
        except Exception as e:
            print(f"⚠️ Не удалось установить аватарку: {e}")

    async def load_existing_bot(self, username):
        """Загрузка существующего бота"""
        print(f"🔍 Загрузка бота @{username}...")
        try:
            async with self.client.conversation('BotFather') as conv:
                await conv.send_message('/token')
                await self.sleep()
                await conv.get_response()
                
                await conv.send_message(f'@{username}')
                await self.sleep()
                response = await conv.get_response()

                if match := re.search(r'(\d+:[a-zA-Z0-9_-]+)', response.text):
                    token = match.group(1)
                    user_id = token.split(':')[0]
                    with open(self.BOT_TOKEN_FILE, 'w') as f:
                        f.write(f"{username}:{user_id}:{token}")

                    await self.set_bot_photo(username)
                    print(f"✅ Бот @{username} успешно загружен!")
                    return username, token

        except Exception as e:
            print(f"❌ Ошибка при загрузке бота: {e}")
        return None, None

    async def check_bot_token(self, token):
        """Проверка валидности токена бота"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.telegram.org/bot{token}/getMe') as resp:
                    data = await resp.json()
                    return resp.status == 200 and data.get('ok', False)
        except Exception:
            return False

    async def run(self):
        """Основной цикл работы бота"""
        try:
            await self.client.start()
            print(f"🔑 Авторизован как: {(await self.client.get_me()).first_name}")

            if not os.path.exists(self.BOT_TOKEN_FILE) or os.stat(self.BOT_TOKEN_FILE).st_size == 0:
                choice = input("Файл токена пуст. Загрузить существующего бота? (да/нет): ").strip().lower()
                
                if choice == 'да':
                    username = input("Введите юзернейм бота (без @): ").strip()
                    result = await self.load_existing_bot(username)
                    
                    if not result:
                        print("🛑 Продолжение невозможно без токена бота")
                        return
                    username, token = result
                else:
                    result = await self.create_new_bot()
                    if not result:
                        print("🛑 Продолжение невозможно без токена бота")
                        return
                    username, user_id, token = result
            else:
                with open(self.BOT_TOKEN_FILE, 'r') as f:
                    content = f.read().strip()
                    if content.count(':') >= 2:
                        parts = content.split(':')
                        username = parts[0]
                        user_id = parts[1]
                        token = ':'.join(parts[2:])
                    else:
                        print("❌ Неверный формат файла токена")
                        return

                if not await self.check_bot_token(token):
                    print("❌ Недействительный токен бота")
                    return

            # Запуск modules.py с передачей клиента
            from modules import main as modules_main
            await modules_main(self.client)

        except Exception as e:
            print(f"🛑 Критическая ошибка: {e}")
        finally:
            if self.client.is_connected():
                await self.client.disconnect()

if __name__ == '__main__':
    bot = BotManager()
    asyncio.run(bot.run())
