import os
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from telegram import Bot

# Telegram setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

# Flask setup for Render
app = Flask(__name__)

# Setup Selenium headless browser
def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

# URLs to monitor
URLS = {
    "Zürich": "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur & Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil": "https://www.woko.ch/de/zimmer-in-waedenswil"
}

def check_woko_rooms():
    driver = create_driver()

    for location, url in URLS.items():
        print(f"🔁 Checking {location}...")

        try:
            driver.get(url)
            time.sleep(5)  # Wait for JavaScript content to load

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            listings = soup.find_all("div", class_="grid-item")

            if listings:
                newest = listings[0]
                title = newest.find("h3").get_text(strip=True) if newest.find("h3") else "No title"
                link = "https://www.woko.ch" + newest.find("a")["href"] if newest.find("a") else url
                message = f"🏠 New listing on WOKO ({location}):\n<b>{title}</b>\n🔗 {link}"
                print(message)
                bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
            else:
                print(f"⚠️ No listings found on WOKO for {location}.")
                bot.send_message(chat_id=CHAT_ID, text=f"⚠️ No listings found on WOKO for {location}.")

        except Exception as e:
            error_msg = f"❌ Error checking {location}: {e}"
            print(error_msg)
            bot.send_message(chat_id=CHAT_ID, text=error_msg)

    driver.quit()

@app.route('/')
def home():
    return "WOKO Bot is running!"

if __name__ == '__main__':
    print("🤖 Bot running...")
    check_woko_rooms()
    app.run(host="0.0.0.0", port=8080)
