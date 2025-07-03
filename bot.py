# bot.py  — WOKO watcher
# hard-coded credentials per user request
TOKEN  = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHATID = "194010292"

import time, logging, threading, shutil, os
from typing import List, Tuple
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ───────────────────────── Telegram ──────────────────────────
def tg_send(text: str) -> None:
    """Send a message to our Telegram chat."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHATID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logging.warning("Telegram send failed: %s", e)

# ─────────────────────── Selenium driver ─────────────────────
def locate_chrome() -> str | None:
    """Return path of Chromium/Chrome binary if present."""
    for candidate in (
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    return None

def new_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    chrome_path = locate_chrome()
    if chrome_path:
        opts.binary_location = chrome_path
    else:
        raise RuntimeError("Chromium binary not found in container")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

# ──────────────────────── Scraping part ──────────────────────
PAGES: List[Tuple[str, str]] = [
    ("Zürich",               "https://www.woko.ch/de/zimmer-in-zuerich"),
    ("Winterthur/Wädenswil", "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil"),
    ("Wädenswil",            "https://www.woko.ch/de/zimmer-in-waedenswil"),
]

def newest_listing(driver: webdriver.Chrome, url: str) -> Tuple[str, str] | None:
    driver.get(url)
    time.sleep(2)

    # Click the “Free rooms” tab if it exists
    try:
        free_btn = driver.find_element(
            By.XPATH,
            '//a[contains(translate(.,"FREE","free"),"free rooms")]',
        )
        free_btn.click()
        time.sleep(2)
    except Exception:
        pass  # tab not present – fine

    soup = BeautifulSoup(driver.page_source, "html.parser")
    card = soup.select_one("div.grid-item")
    if not card:
        return None

    title = card.find("h3").get_text(strip=True)
    link = "https://www.woko.ch" + card.find("a")["href"]
    return title, link

def scrape_once() -> None:
    with new_driver() as drv:
        for name, url in PAGES:
            logging.info("Checking %s …", name)
            result = newest_listing(drv, url)
            if not result:
                tg_send(f"⚠️ Kein Inserat für <b>{name}</b>")
                continue
            title, link = result
            tg_send(f"🏠 <b>{title}</b>\n🔗 {link}")

# ────────────────── Background loop + Flask app ──────────────
app = Flask(__name__)

@app.route("/")
def root() -> Response:
    return Response("✅ WOKO bot running", 200)

def loop() -> None:
    beat = 0
    while True:
        logging.info("HB %d", beat)
        beat = (beat + 1) % 60
        try:
            scrape_once()
        except Exception as e:
            logging.exception("scrape_once failed: %s", e)
            tg_send(f"❌ Bot error:\n<code>{e}</code>")
        time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    threading.Thread(target=loop, daemon=True).start()
    PORT = 10000
    app.run(host="0.0.0.0", port=PORT)
