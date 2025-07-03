import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
TELEGRAM_TOKEN = 'YOUR_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID'  # Replace with your chat ID

# === SEND MESSAGE ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram exception: {e}")

# === CHECK SINGLE WOKO PAGE ===
def check_woko_page(driver, url, label):
    try:
        driver.get(url)

        # Accept cookies if present
        try:
            accept_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Alle akzeptieren")]'))
            )
            accept_btn.click()
            print("🍪 Cookies accepted")
        except:
            print("🍪 No cookie banner")

        # Wait for listings to load
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "item"))
        )

        listings = driver.find_elements(By.CLASS_NAME, "item")

        if not listings:
            send_telegram_message(f"⚠️ No listings found on WOKO for {label}.")
            print(f"⚠️ No listings found on WOKO for {label}.")
            return

        # Get first listing details
        listing = listings[0]
        title = listing.find_element(By.CLASS_NAME, "title").text
        address = listing.find_element(By.CLASS_NAME, "address").text
        rent = listing.find_element(By.CLASS_NAME, "price").text if listing.find_elements(By.CLASS_NAME, "price") else "N/A"

        msg = f"<b>{label}</b>\n🏠 {title}\n📍 {address}\n💰 {rent}\n🔗 <a href='{url}'>See all listings</a>"
        send_telegram_message(msg)
        print(f"✅ Sent listing from {label}")

    except Exception as e:
        send_telegram_message(f"❌ Error while checking {label}: {e}")
        print(f"❌ Error while checking {label}: {e}")

# === CHECK ALL LOCATIONS ===
def check_all_woko_pages():
    print("🔁 Checking WOKO pages...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        pages = [
            ("https://www.woko.ch/de/zimmer-in-zuerich", "Zürich"),
            ("https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil", "Winterthur & Wädenswil"),
            ("https://www.woko.ch/de/zimmer-in-waedenswil", "Wädenswil"),
        ]
        for url, label in pages:
            check_woko_page(driver, url, label)
            time.sleep(1)  # short delay between checks
    finally:
        driver.quit()

# === MAIN LOOP ===
if __name__ == "__main__":
    while True:
        check_all_woko_pages()
        time.sleep(60)  # wait 1 minute before next check
