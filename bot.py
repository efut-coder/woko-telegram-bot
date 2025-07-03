print("🤖 Bot started. Checking WOKO every minute...")

import os
import time
import requests

# ✅ Вызов keep_alive (если ты его используешь на Replit или Render)
from keep_alive import keep_alive
keep_alive()

# ✅ Переменные из окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ✅ Функция отправки сообщения
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    print(f"⚡ Sending to Telegram: {message}")
    print("✅ Telegram response:", response.status_code, response.text)

# ✅ Тестовая подмена настоящего парсера
def get_free_rooms():
    # Всегда возвращает одну фейковую "новую" комнату
    return ["<b>🔔 Test room!</b>\n<a href='https://woko.ch'>Open listing</a>"]

# ✅ Основной цикл
while True:
    print("⏳ Tick... checking WOKO again...")
    new_rooms = get_free_rooms()
    for msg in new_rooms:
        send_telegram_message(msg)
    time.sleep(60)
