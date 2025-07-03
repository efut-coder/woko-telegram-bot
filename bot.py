print("🤖 Bot started. Checking WOKO every minute...")

import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# === Keep-alive for Render ===
from keep_alive import keep_alive
keep_alive()

# === Telegram credentials from environment ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
sent_links = set()

# === Send message via Telegram ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    return response.json()

# === Check WOKO for new rooms ===
def get_free_rooms():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)

        driver.get("https://www.woko.ch/en/zimmer-in-zuerich")
        time.sleep(3)  # Wait for page load

        # Accept cookies
        try:
            accept_button = driver.find_element(By.ID, "cookie-agree")
            accept_button.click()
            time.sleep(1)
        except:
            pass  # If already accepted

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        listings = soup.select("div.content-container div.row.offer")
        new_announcements = []

        for listing in listings:
            link_tag = listing.find("a", href=True)
            title_tag = listing.find("h3")
            if not link_tag or not title_tag:
                continue

            full_link = "https://www.woko.ch" + link_tag["href"]
            title = title_tag.get_text(strip=True)

            formatted = f"<b>{title}</b>\n<a href='{full_link}'>Open listing</a>"
            new_announcements.append(formatted)
            break  # Send only one latest for testing

        return new_announcements

    except Exception as e:
        driver.quit()
        return [f"❗️Error: {str(e)}"]

# === Run the bot ===
print("🟢 Bot is running.")
while True:
    new_rooms = get_free_rooms()
    for msg in new_rooms:
        send_telegram_message(msg)
    time.sleep(60)
