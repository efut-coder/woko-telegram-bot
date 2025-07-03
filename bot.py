import os
import time
import requests
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ✅ Telegram credentials
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ✅ Flask server to keep bot alive
app = Flask('')

@app.route('/')
def home():
    return "WOKO bot is running."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ✅ Send Telegram message
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

# ✅ Check WOKO site (no Free rooms click)
def check_woko():
    print("🔁 Checking WOKO...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.woko.ch/en/zimmer-in-zuerich")
        time.sleep(3)

        # Accept cookies if shown
        try:
            accept_button = driver.find_element(By.ID, "cookie-notice-accept")
            accept_button.click()
            print("🍪 Cookies accepted")
            time.sleep(1)
        except:
            print("🍪 No cookies popup")

        # Parse current page without clicking anything
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.content-container div.row.offer")

        if not listings:
            send_telegram_message("❌ No listings found on WOKO.")
            print("⚠️ No listings found")
            return

        # Send latest (first) listing
        latest = listings[0]
        link_tag = latest.find("a", href=True)
        title_tag = latest.find("h3")

        if link_tag and title_tag:
            full_link = "https://www.woko.ch" + link_tag['href']
            title = title_tag.get_text(strip=True)
            message = f"<b>{title}</b>\n<a href=\"{full_link}\">Open listing</a>"
            send_telegram_message(message)
            print("✅ Sent latest listing to Telegram")
        else:
            send_telegram_message("⚠️ Couldn't extract latest listing.")
            print("❌ Missing data in latest listing")

    except Exception as e:
        print("❌ Error:", e)
        send_telegram_message(f"Error: {str(e)}")

    finally:
        driver.quit()

# ✅ Start the bot
keep_alive()
print("🤖 Bot started (no Free rooms click)")

# Only run once for testing
check_woko()
