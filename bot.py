import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from keep_alive import keep_alive

keep_alive()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
sent_links = set()

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, data=payload)
    print(f"📨 Sent to Telegram ({response.status_code}): {message}")

def get_all_rooms_from_homepage():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.woko.ch/")
        time.sleep(2)

        # Accept cookies if needed
        try:
            cookie_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept all cookies')]")
            cookie_button.click()
            print("🍪 Accepted cookies.")
            time.sleep(1)
        except:
            print("🍪 No cookie button found.")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        listings = soup.select("div.content-container div.row.offer")
        new_announcements = []

        for listing in listings:
            link_tag = listing.find("a", href=True)
            title_tag = listing.find("h3")
            if not link_tag or not title_tag:
                continue

            full_link = "https://www.woko.ch" + link_tag['href']
            title = title_tag.get_text(strip=True)

            # Always send the first listing for testing
formatted = f"<b>{title}</b>\n<a href='{full_link}'>Open listing</a>"
new_announcements.append(formatted)
break  # отправим только одно последнее

        return new_announcements

    except Exception as e:
        driver.quit()
        print("⚠️ Error while fetching homepage:", e)
        return []

# Main loop
print("🤖 Bot started. Checking WOKO homepage every minute...")

while True:
    print("⏳ Tick... checking again...")
    rooms = get_all_rooms_from_homepage()
    if rooms:
        for msg in rooms:
            send_telegram_message(msg)
    else:
        print("🔍 No new listings.")
    time.sleep(60)
