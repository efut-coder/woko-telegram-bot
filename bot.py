print("🤖 Bot started. Checking WOKO every minute...")

import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from keep_alive import keep_alive

keep_alive()

# Чтение токенов из окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_free_rooms():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)

        driver.get("https://www.woko.ch/en/zimmer-in-zuerich")
        time.sleep(5)  # Ждем, чтобы сайт подгрузил контент

        # Принимаем cookies
        try:
            accept_button = driver.find_element(By.ID, "cookie-agree")
            accept_button.click()
            time.sleep(2)
        except:
            pass  # Кнопки может не быть

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        # Отладка: отправляем HTML
        preview = soup.prettify()[:2000]
        return [f"🔍 HTML Preview:\n<pre>{preview}</pre>"]

    except Exception as e:
        driver.quit()
        return [f"❗️Error: {str(e)}"]

# Основной цикл
while True:
    print("🔁 Tick... checking WOKO again")
    new_rooms = get_free_rooms()
    for msg in new_rooms:
        send_telegram_message(msg)
    time.sleep(60)
