# bot.py
#
# WOKO room-watcher bot
# ---------------------
# • Scrapes three WOKO pages (Zürich, Winterthur/Wädenswil, Wädenswil)
# • Clicks the “Free rooms” tab where it exists
# • Sends the newest listing (or “Kein Inserat …” if none) to Telegram
# • Runs every 60 s in a background thread
#
# ⚙️  Environment variables required on Render:
#     TELEGRAM_TOKEN   – your bot token
#     TELEGRAM_CHAT_ID – the chat / user id that will receive the messages
# --------------------------------------------------------------

import os, time, logging, threading
from datetime import datetime as dt
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup
from flask import Flask, Response

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────────────────────────────────────
# 1.  Telegram helpers
# ──────────────────────────────────────────────────────────────
TOKEN  = os.getenv("TELEGRAM_TOKEN",  "")
CHATID = os.getenv("TELEGRAM_CHAT_ID", "")

def tg_send(text: str) -> None:
    if not (TOKEN and CHATID):
        logging.warning("Telegram creds missing → message not sent")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHATID,
        "text":    text,
        "parse_mode": "HTML"
    }, timeout=10)


# ──────────────────────────────────────────────────────────────
# 2.  Selenium driver factory
# ──────────────────────────────────────────────────────────────
def new_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    # 👇 tell Selenium where Render installs Chromium
    opts.binary_location = "/usr/bin/chromium"

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# ──────────────────────────────────────────────────────────────
# 3.  Scraping logic
# ──────────────────────────────────────────────────────────────
PAGES: List[Tuple[str, str]] = [
    ("Zürich",              "https://www.woko.ch/de/zimmer-in-zuerich"),
    ("Winterthur/Wädenswil","https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil"),
    ("Wädenswil",           "https://www.woko.ch/de/zimmer-in-waedenswil")
]

def newest_listing_html(driver: webdriver.Chrome, url: str) -> BeautifulSoup:
    driver.get(url)
    time.sleep(2)  # let JS build the page

    # If a “Free rooms” tab/button exists → click it
    try:
        free = driver.find_element(By.XPATH, '//a[contains(translate(.,"FREE","free"),"free rooms")]')
        free.click()
        time.sleep(2)
    except Exception:
        pass  # no such button on that page

    return BeautifulSoup(driver.page_source, "html.parser")

def scrape_once() -> None:
    with new_driver() as driver:
        for name, url in PAGES:
            logging.info("GET %s …", name)
            soup = newest_listing_html(driver, url)
            items = soup.select("div.grid-item")

            if not items:
                tg_send(f"⚠️ Kein Inserat für <b>{name}</b>")
                continue

            first = items[0]
            title = first.find("h3").get_text(strip=True)
            href  = first.find("a")["href"]
            full  = "https://www.woko.ch" + href

            msg = f"🏠 <b>{title}</b>\n🔗 {full}"
            tg_send(msg)


# ──────────────────────────────────────────────────────────────
# 4.  Background loop & Flask keep-alive
# ──────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home() -> Response:
    return Response("✅ WOKO bot alive", 200)

def loop() -> None:
    hb = 0
    while True:
        logging.info("HB %d", hb)
        hb = (hb + 1) % 60
        try:
            scrape_once()
        except Exception as e:
            logging.exception("scrape_once() failed: %s", e)
            tg_send(f"❌ Bot error:\n<code>{e}</code>")
        time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # start the scraper thread
    threading.Thread(target=loop, daemon=True).start()

    # start Flask so Render sees an open port
    port = int(os.getenv("PORT", "10000"))
    logging.info("Flask binding to port %d", port)
    app.run(host="0.0.0.0", port=port)
