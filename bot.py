import os
import time
import requests
from flask import Flask
from threading import Thread
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ✅ Telegram bot credentials
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ✅ Flask app to keep Render alive
app = Flask('')

@app.route('/')
def home():
    return "✅ WOKO Bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# ✅ Send Telegram message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# ✅ Check WOKO homepage
def check_woko():
    print("🔁 Checking WOKO homepage...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.woko.ch")
        time.sleep(2)

        # Accept cookies
        try:
            accept = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Accept all")]'))
            )
            accept.click()
            print("🍪 Cookies accepted")
            time.sleep(1)
        except:
            print("🍪 No cookie banner")

        # Wait for listings to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.room-item"))
        )

        listings = driver.find_elements(By.CSS_SELECTOR, "div.room-item")

        if not listings:
            print("⚠️ No listings found on WOKO.")
            send_telegram_message("⚠️ No listings found on WOKO.")
            return

        # Get first (most recent) listing
        latest = listings[0]
        title = latest.find_element(By.TAG_NAME, "h3").text.strip()
        link = latest.find_element(By.TAG_NAME, "a").get_attribute("href")
        date = latest.find_element(By.CSS_SELECTOR, ".date").text.strip()

        message = f"<b>{title}</b>\n🗓 {date}\n<a href=\"{link}\">Open listing</a>"
        send_telegram_message(message)
        print("✅ Sent latest listing to Telegram")

    except Exception as e:
        print("❌ Error:", e)
        send_telegram_message(f"❌ Bot error: {e}")
    finally:
        driver.quit()

# ✅ Start bot
keep_alive()
print("🤖 Bot running...")

while True:
    check_woko()
    time.sleep(60)
