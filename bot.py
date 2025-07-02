print("🤖 Bot started. Checking WOKO every minute...")

import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from keep_alive import keep_alive  # Flask app to prevent Render timeout

keep_alive()

# Load environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
sent_links = set()

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Missing Telegram credentials.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload)
        print(f"✅ Sent message: {message}")
    except Exception as e:
        print(f"❌ Error sending Telegram message: {str(e)}")

def get_free_rooms():
    print("🌐 Accessing WOKO site...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.woko.ch/en/zimmer-in-zuerich")
        button = driver.find_element(By.XPATH, '//a[contains(text(), "Free rooms")]')
        button.click()
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        listings = soup.select("div.content-container div.row.offer")
        rooms = []

        for listing in listings:
            link_tag = listing.find("a", href=True)
            title_tag = listing.find("h3")
            if not link_tag or not title_tag:
                continue
            full_link = "https://www.woko.ch" + link_tag['href']
            title = title_tag.get_text(strip=True)
            if full_link not in sent_links:
                sent_links.add(full_link)
                rooms.append(f"<b>{title}</b>\n<a href=\"{full_link}\">Open listing</a>")
        print(f"✅ Found {len(rooms)} new rooms")
        return rooms
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def run_bot_loop():
    print("🔁 Bot loop started...")
    while True:
        print("🔎 Tick... checking again")
        new_rooms = get_free_rooms()
        for msg in new_rooms:
            send_telegram_message(msg)
        time.sleep(60)

# Start the bot loop in a separate thread
threading.Thread(target=run_bot_loop).start()
