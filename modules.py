import os
import random
import string
import subprocess
import asyncio
import platform
from telethon import events, TelegramClient
from datetime import datetime, timedelta
from config import TOKEN_FILE, API_ID, API_HASH
import telethon 
import requests

# В начале файла
start_time = datetime.now()  # Сохраняем время старта

# Глобальные переменные для отслеживания статистики
received_messages_count = 0
sent_messages_count = 0
active_users = set()  # Храним уникальных пользователей

def translate_text(text, target_lang):
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={target_lang}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["responseData"]["translatedText"]
    else:
        return "Ошибка перевода."

@client.on(events.NewMessage)
async def handler(event):
    if event.message.message.startswith('.tr '):
        parts = event.message.message.split(' ', 2)
        if len(parts) != 3:
            await event.reply('Используйте: .tr <код языка> <текс для перевода>')
            return
        
        target_lang = parts[1]
        text_to_translate = parts[2]

        # Переводим текст
        translated_text = translate_text(text_to_translate, target_lang)

        # Изменяем исходное сообщение
        await event.message.edit(translated_text)

# Создание экземпляра переводчика
def register_event_handlers(client):
    @client.on(events.NewMessage(pattern=r'\.tr (\w+)'))
    async def translate_handler(event):
        global received_messages_count, active_users
        received_messages_count += 1
        active_users.add(event.sender_id)
        
        if event.is_reply:
            target_language = event.message.text.split(' ')[1].strip()
            replied_message = await event.get_reply_message()
            
            if replied_message:
                text_to_translate = replied_message.message
                try:
                    translator = get_translator(target_language)
                    translated_text = translator.translate(text_to_translate)

                    await event.reply(translated_text)
                except Exception as e:
                    await event.reply(f"❌ Ошибка при переводе: {str(e)}")
            else:
                await event.reply("❌ Ошибка: Не удалось получить сообщение для перевода.")
        else:
            await event.reply("❗ Используйте эту команду в ответ на сообщение, которое нужно перевести.")
            
class DeferredMessage:
    def __init__(self, client):
        self.client = client
        self.interval = 3600  # По умолчанию, 1 час
        self.message_count = 10  # По умолчанию, 10 сообщений

    async def отложка(self, event):
        global sent_messages_count
        args = event.message.message.split(' ', 3)

        if len(args) < 4:
            await event.edit("❗ Пожалуйста, укажите количество сообщений, период (в минутах) и текст.")
            return
        
        try:
            self.message_count = int(args[1].strip())
            self.interval = int(args[2].strip()) * 60  # Конвертируем минуты в секунды
        except ValueError:
            await event.edit("❌ Пожалуйста, укажите корректные числовые значения.")
            return
        
        text = args[3].strip()
        
        if not text:
            await event.edit("✋ Пожалуйста, укажите текст сообщения.")
            return

        await event.edit(f"✅ Сообщения успешно запланированы!\n\n"
                         f"📅 Запланировано отправить {self.message_count} сообщений с интервалом в {self.interval // 60} минут(ы).")

        chat_id = event.chat_id
        
        for i in range(self.message_count):
            send_time = datetime.now() + timedelta(seconds=self.interval * i)
            await self.client.send_message(chat_id, text, schedule=send_time)
            sent_messages_count += 1  # Увеличиваем счётчик отправленных сообщений

        final_message = (f"📤 Запланированные сообщения будут отправлены!\n"
                         f"⏳ Следующее сообщение через {self.interval // 60} минут(ы).")

        await self.client.send_message(chat_id, final_message)



def register_event_handlers(client):
    deferred_message = DeferredMessage(client)

    @client.on(events.NewMessage(pattern=r'\.отложка'))
    async def handler(event):
        global received_messages_count, active_users
        received_messages_count += 1  # Увеличиваем счётчик полученных сообщений
        active_users.add(event.sender_id)  # Добавляем пользователя в активные пользователи
        await deferred_message.отложка(event)

    @client.on(events.NewMessage(pattern=r'\.info'))
    async def info_handler(event):
        uptime = datetime.now() - start_time  # Рассчитываем время работы 
        uptime_str = str(uptime).split('.')[0]  # Убираем миллисекунды

        device = platform.system()
        device_info = platform.platform()
        user_name = event.sender.first_name  # Имя владельца аккаунта
        current_status = "Активен"  # Устанавливаем текущий статус

        info_message = (
            f"🔍 **Acroka - UserBot**:\n\n"
            f"👤 **Владелец** {user_name}\n"
            f"💻 **Платформа:** {device}\n"
            f"⏳ **Uptime:** {uptime_str}\n"
            f"✨ **Версия Telethon:** {telethon.__version__}\n" 
            f"📥 **Sent:** {received_messages_count}\n"
            f"📤 **Accepted:** {sent_messages_count}\n"
            f"🟢 **Статус:** {current_status}\n"
            f"👥 **Количество активных пользователей:** {len(active_users)}\n"
        )

        await event.edit(info_message)

    @client.on(events.NewMessage(pattern=r'\.ping'))
    async def ping_handler(event):
        process = subprocess.Popen(['ping', '-c', '1', 'google.com'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            result = "✅ **Пинг к Google: Время: {}мс**".format(stdout.decode().split('time=')[1].split(' ')[0])
        else:
            result = "❌ **Ошибка пинга!**"

        await event.edit(result)

def generate_username():
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    return f'acroka_{random_part}_bot'

async def create_bot(client):
    botfather = await client.get_input_entity('BotFather')
    bot_title = 'Acroka'

    await client.send_message(botfather, '/newbot')
    await asyncio.sleep(2)
    await client.send_message(botfather, bot_title)
    await asyncio.sleep(2)

    username = generate_username()
    await client.send_message(botfather, username)
    await asyncio.sleep(5)

    async for message in client.iter_messages(botfather, limit=10):
        if 'Use this token to access the HTTP API:' in message.message:
            lines = message.message.split('\n')
            for i, line in enumerate(lines):
                if 'Use this token to access the HTTP API:' in line and i + 1 < len(lines):
                    token = lines[i + 1].strip()
                    break
            else:
                return None, None
            break
    else:
        return None, None

    user_id = token.split(':')[0]
    with open(TOKEN_FILE, 'w') as f:
        f.write(f"{username}:{user_id}:{token}")
    
    return username, user_id, token

async def run_bot(client, token):
    bot_client = TelegramClient('bot', API_ID, API_HASH)
    await bot_client.start(bot_token=token)

    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        await event.reply('👋 Привет! Я - Acroka, твой userbot!\n\n'
                           '💡 Для просмотра основных команд используй `.help`.')

    await bot_client.run_until_disconnected()
