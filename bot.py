#!/usr/bin/env python3
"""
WOKO-watcher → Telegram
Checks Zürich / Winterthur + Wädenswil / Wädenswil pages,
clicks the “Free rooms” button, and sends the newest listing
to your Telegram chat every minute.
"""

import os, time, threading, logging, requests
from dotenv import load_dotenv

from flask import Flask
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────  CONFIG  ──────────────────────────
load_dotenv()                                # read .env if present
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID        = os.getenv("CHAT_ID")        # numeric chat ID

URLS = {
    "Zürich":        "https://www.woko.ch/en/zimmer-in-zuerich",
    "Winterthur & Wädenswil":
                     "https://www.woko.ch/en/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil":     "https://www.woko.ch/en/zimmer-in-waedenswil",
}

CHECK_INTERVAL = 60        # seconds
FLASK_PORT     = 10000     # Render will expose this automatically
# ──────────────────────────────────────────────────────────────


# ----------  helpers ----------
def telegram_send(text: str) -> None:
    """Post a message to Telegram (HTML enabled)."""
    if not (TELEGRAM_TOKEN and CHAT_ID):
        logging.error("TELEGRAM_TOKEN or CHAT_ID missing!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logging.exception("Telegram send failed: %s", e)


def new_driver() -> webdriver.Chrome:
    """Headless Chrome with webdriver-manager."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())  # <- fixed
    return webdriver.Chrome(service=service, options=opts)


# ----------  scraper ----------
def scrape_once() -> None:
    logging.debug("entered scrape_once()")
    with new_driver() as driver:
        for location, url in URLS.items():
            logging.info("GET %s …", location)
            driver.get(url)
            time.sleep(2)

            # click the big “Free rooms” button if it exists
            try:
                btn = driver.find_element(
                    "xpath",
                    '//a[contains(translate(.,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),'
                    '"free rooms")]',
                )
                btn.click()
                time.sleep(2)
            except Exception:
                pass  # button just isn’t there

            soup = BeautifulSoup(driver.page_source, "html.parser")
            boxes = soup.select("div.grid-item")  # each advert box

            if not boxes:
                telegram_send(f"⚠️ Kein Inserat für <b>{location}</b>.")
                continue

            # newest listing is first in the HTML
            box   = boxes[0]
            title = box.find("h3").get_text(strip=True)
            link  = box.find("a", href=True)
            href  = link["href"] if link else url
            if href.startswith("/"):
                href = "https://www.woko.ch" + href

            telegram_send(f"🏠 <b>{title}</b>\n🔗 {href}")


# ----------  heartbeat thread ----------
def loop() -> None:
    minute = 0
    while True:
        logging.info("HB %d", minute)
        scrape_once()
        minute += 1
        time.sleep(CHECK_INTERVAL)


# ----------  Flask “keep-alive” ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ WOKO bot running"


# ----------  main ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=FLASK_PORT)
