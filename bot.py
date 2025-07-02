print("🤖 Bot started. Checking WOKO every minute...")

import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from keep_alive import keep_alive

# Start keep_alive server for Render pinging
keep_alive()

# Load Telegram token and chat ID from Render environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
sent_links = set()

print("🛠 Environment loaded")
print(f"✅ Telegram token starts with: {TELEGRAM_TOKEN[:5]}")
print(f"✅ Chat ID: {CHAT_ID}")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        print(f"📨 Message sent: {message}")
        print(f"Telegram response: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def get_free_rooms():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.woko.ch/en/zimmer-in-zuerich")

    try:
        print("🌐 Accessing WOKO site...")
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
        driver.quit()
        print(f"❌ Error while scraping: {e}")
        return [f"Error: {str(e)}"]

# Main loop
while True:
    print("🔁 Tick... checking again")
    new_rooms = get_free_rooms()
    for msg in new_rooms:
        send_telegram_message(msg)
    time.sleep(60)
