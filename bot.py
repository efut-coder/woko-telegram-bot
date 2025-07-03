import os
import time
import requests
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ✅ Telegram bot credentials from environment
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ✅ Simple Flask app to keep it alive
app = Flask('')

@app.route('/')
def home():
    return "✅ WOKO bot is running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ✅ Send message to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

# ✅ Track already sent links
sent_links = set()

# ✅ Main function: check WOKO for new listings
def check_woko():
    print("🔁 Tick... checking WOKO again")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.woko.ch/en/zimmer-in-zuerich")
        time.sleep(2)

        # Click "Free rooms"
        free_button = driver.find_element(By.XPATH, '//a[contains(text(), "Free rooms")]')
        free_button.click()
        time.sleep(3)

        # Parse new page
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listings = soup.select("div.content-container div.row.offer")
        new_found = 0

        for listing in listings:
            link_tag = listing.find("a", href=True)
            title_tag = listing.find("h3")

            if not link_tag or not title_tag:
                continue

            full_link = "https://www.woko.ch" + link_tag['href']
            title = title_tag.get_text(strip=True)

            if full_link not in sent_links:
                sent_links.add(full_link)
                message = f"<b>{title}</b>\n<a href=\"{full_link}\">Open listing</a>"
                send_telegram_message(message)
                new_found += 1

        print(f"✅ {new_found} new listing(s) sent")
        driver.quit()
    except Exception as e:
        print("❌ Error:", e)
        driver.quit()

# ✅ Start bot
keep_alive()
print("🤖 Bot started. Checking WOKO every minute...")

while True:
    check_woko()
    time.sleep(60)
