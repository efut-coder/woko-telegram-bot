import os
import time
import requests
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ✅ Environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ✅ Flask app to keep bot alive
app = Flask('')

@app.route('/')
def home():
    return "✅ WOKO Bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# ✅ Telegram sender
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

# ✅ WOKO listing checker for multiple URLs
def check_woko():
    print("🔁 Checking WOKO pages...")
    urls = [
        ("Zürich", "https://www.woko.ch/de/zimmer-in-zuerich"),
        ("Winterthur & Wädenswil", "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil"),
        ("Wädenswil", "https://www.woko.ch/de/zimmer-in-waedenswil")
    ]

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    for region, url in urls:
        try:
            driver.get(url)
            time.sleep(3)

            # Accept cookies if shown
            try:
                accept_btn = driver.find_element(By.XPATH, '//button[contains(text(), "Alle akzeptieren")]')
                accept_btn.click()
                print("🍪 Cookies accepted")
                time.sleep(2)
            except:
                print("🍪 No cookie banner")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            listings = soup.select("div.view-content > div")

            print(f"🔍 {region}: Found {len(listings)} listings")

            if listings:
                first = listings[0]
                title = first.find("div", class_="views-field-title")
                location = first.find("div", class_="views-field-field-adress")
                rent = first.find("div", class_="views-field-field-miete")
                date = first.find("span", class_="date-display-single")

                message = f"<b>🏠 New Room Listing ({region})</b>\n"
                if title:
                    message += f"\n<b>{title.get_text(strip=True)}</b>"
                if location:
                    message += f"\n📍 {location.get_text(strip=True)}"
                if rent:
                    message += f"\n💰 {rent.get_text(strip=True)}"
                if date:
                    message += f"\n🗓 {date.get_text(strip=True)}"
                message += f"\n🔗 <a href=\"{url}\">View Listings</a>"

                send_telegram_message(message)
                print(f"✅ Sent 1st listing for {region}")
            else:
                send_telegram_message(f"⚠️ No listings found on WOKO for {region}.")

        except Exception as e:
            print(f"❌ Error checking {region}: {e}")
            send_telegram_message(f"❌ Bot error for {region}: {e}")

    driver.quit()

# ✅ Start
keep_alive()
print("🤖 Bot running...")

while True:
    check_woko()
    time.sleep(60)
