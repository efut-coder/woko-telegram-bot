import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "✅ Это тестовое сообщение от бота!",
    "parse_mode": "HTML"
}

response = requests.post(url, data=payload)
print("Status:", response.status_code)
print("Response:", response.text)
