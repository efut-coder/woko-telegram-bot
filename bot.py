import os
import time
import threading
import requests
from flask import Flask
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID", "YOUR_CHAT_ID")

# === FLASK APP to keep alive ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ WOKO Bot is running"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === SEND TELEGRAM MESSAGE ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")

# === CHECK ONE WOKO PAGE ===
def check_woko_page(driver, url, label):
    try:
        driver.get(url)
        print(f"🌍 Opened {label} page")

        # Accept cookie banner
        try:
            accept_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Alle akzeptieren")]'))
            )
            accept_btn.click()
            print("🍪 Cookies accepted")
        except:
            print("🍪 No cookie popup")

        # Wait for listings
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "item"))
        )

        listings = driver.find_elements(By.CLASS_NAME, "item")
        if not listings:
            send_telegram_message(f"⚠️ No listings found on WOKO for {label}.")
            return

        first = listings[0]
        title = first.find_element(By.CLASS_NAME, "title").text
        address = first.find_element(By.CLASS_NAME, "address").text
        rent = first.find_element(By.CLASS_NAME, "price").text if first.find_elements(By.CLASS_NAME, "price") else "N/A"

        msg = f"<b>{label}</b>\n🏠 {title}\n📍 {address}\n💰 {rent}\n🔗 <a href='{url}'>See all listings</a>"
        send_telegram_message(msg)
        print(f"✅ Sent listing for {label}")

    except Exception as e:
        print(f"❌ Error on {label}: {e}")
        send_telegram_message(f"❌ Error while checking {label}: {e}")

# === CHECK ALL PAGES ===
def check_all_woko_pages():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    pages = [
        ("https://www.woko.ch/de/zimmer-in-zuerich", "Zürich"),
        ("https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil", "Winterthur & Wädenswil"),
        ("https://www.woko.ch/de/zimmer-in-waedenswil", "Wädenswil")
    ]

    for url, label in pages:
        check_woko_page(driver, url, label)
        time.sleep(2)

    driver.quit()

# === MAIN BOT LOOP ===
def bot_loop():
    while True:
        print("🔁 Checking WOKO pages...")
        check_all_woko_pages()
        time.sleep(60)

# === START EVERYTHING ===
if __name__ == "__main__":
    print("🤖 Bot running...")
    threading.Thread(target=run_flask).start()  # keeps the app alive on Render
    bot_loop()
