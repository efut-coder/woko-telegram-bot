import os
import time
import requests
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ✅ Environment variables for your Telegram bot
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ✅ Flask app to keep alive on Render
app = Flask('')

@app.route('/')
def home():
    return "✅ WOKO Bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# ✅ Send a Telegram message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    print("📨 Telegram response:", response.text)

# ✅ Main check function
def check_woko():
    print("🔁 Checking WOKO homepage...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.woko.ch")
        time.sleep(3)

        # Accept cookies if shown
        try:
            accept_btn = driver.find_element(By.XPATH, '//button[contains(text(), "Accept all")]')
            accept_btn.click()
            print("🍪 Cookies accepted")
            time.sleep(2)
        except:
            print("🍪 No cookie popup found")

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # ✅ FIXED: Correct selector based on real listings
        listings = soup.select("div.angebot.teaser")

        if not listings:
            print("⚠️ No listings found")
            send_telegram_message("⚠️ No listings found on WOKO.")
            return

        for box in listings:
            title = box.find("h3")
            date = box.find("p", class_="date")
            address = box.find("div", class_="address")
            rent = box.find("div", class_="price")

            if not (title and date and address):
                continue

            msg = f"<b>{title.get_text(strip=True)}</b>\n🗓 {date.get_text(strip=True)}\n🏠 {address.get_text(strip=True)}"
            if rent:
                msg += f"\n💰 {rent.get_text(strip=True)} CHF"

            send_telegram_message(msg)
            print("✅ Sent latest listing")
            break  # only send the first one for now

        driver.quit()

    except Exception as e:
        print("❌ Error:", e)
        send_telegram_message(f"❌ Bot error: {e}")
        driver.quit()

# ✅ Start bot
keep_alive()
print("🤖 Bot running. Checking WOKO every 60 seconds...")

while True:
    check_woko()
    time.sleep(60)
