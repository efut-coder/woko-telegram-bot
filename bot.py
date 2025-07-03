import os
import time
import requests
import threading
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# === ENV VARIABLES ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# === FLASK KEEP-ALIVE ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ WOKO Bot is running"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === TELEGRAM MESSAGE ===
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
        print(f"❌ Telegram error: {e}")

# === WOKO PARSER ===
def check_woko(url, city_label):
    print(f"🔁 Checking {city_label}...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        time.sleep(3)

        try:
            cookie_btn = driver.find_element(By.XPATH, '//button[contains(text(), "Accept all")]')
            cookie_btn.click()
            time.sleep(1)
            print("🍪 Cookies accepted")
        except:
            print("🍪 No cookie banner")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.select(".listing")

        if not listings:
            send_telegram_message(f"⚠️ No listings found on WOKO for {city_label}.")
            print(f"⚠️ No listings found on WOKO for {city_label}.")
            return

        for item in listings:
            title = item.select_one("h3")
            date = item.select_one(".date")
            address = item.select_one(".address")
            price = item.select_one(".price")

            if title and date and address:
                msg = f"<b>{title.text.strip()}</b>\n🗓 {date.text.strip()}\n🏠 {address.text.strip()}"
                if price:
                    msg += f"\n💰 {price.text.strip()}"
                send_telegram_message(msg)
                print("✅ Sent a listing")
                break  # send only one for now

    except Exception as e:
        print("❌ Error in scraping:", e)
        send_telegram_message(f"❌ Bot error: {e}")
    finally:
        driver.quit()

# === MAIN LOOP ===
def bot_loop():
    urls = [
        ("https://www.woko.ch/de/zimmer-in-zuerich", "Zürich"),
        ("https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil", "Winterthur & Wädenswil"),
        ("https://www.woko.ch/de/zimmer-in-waedenswil", "Wädenswil")
    ]
    while True:
        for url, label in urls:
            check_woko(url, label)
        time.sleep(60)  # every 1 minute

# === START ===
if __name__ == '__main__':
    print("🤖 Bot running...")
    threading.Thread(target=run_flask).start()
    bot_loop()
