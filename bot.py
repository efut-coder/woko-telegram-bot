import time
import requests
import os
from bs4 import BeautifulSoup
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ───────────── Telegram (hard-coded – YOU supplied these) ─────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"

def tg_send(text: str) -> None:
    """Send a single HTML-formatted message to Telegram via HTTP POST."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, data=payload, timeout=10)

# ───────────── Selenium headless Chrome factory ─────────────
def make_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

# ───────────── Pages to watch (German interface) ─────────────
URLS = {
    "Zürich"                 : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil" : "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"              : "https://www.woko.ch/de/zimmer-in-waedenswil"
}

def scrape_once() -> None:
    drv = make_driver()

    for city, url in URLS.items():
        print(f"🔎  Checking {city}")
        try:
            drv.get(url)
            time.sleep(4)           # give JS a moment

            soup = BeautifulSoup(drv.page_source, "html.parser")

            # Works for both older <div class="offer"> and newer <div class="grid-item">
            box = soup.select_one("div.offer, div.grid-item")
            if not box:
                tg_send(f"⚠️ No listings found on WOKO for {city}.")
                continue

            title_tag = box.find(["h3", "h2"])
            link_tag  = box.find("a", href=True)

            title = title_tag.get_text(strip=True) if title_tag else "Kein Titel"
            link  = "https://www.woko.ch" + link_tag["href"] if link_tag else url

            msg = f"🏠 <b>{title}</b>\n🔗 {link}\n📍 {city}"
            tg_send(msg)

        except Exception as e:
            err = f"❌ Fehler bei {city}: {e}"
            print(err)
            tg_send(err)

    drv.quit()

# ─────────────  Flask “keep-alive” endpoint for Render ─────────────
app = Flask(__name__)
@app.route("/")
def root(): return "✅ WOKO bot is running"

# ─────────────  Main loop ─────────────
if __name__ == "__main__":
    print("🤖 Bot has started …")

    scrape_once()          # run immediately

    while True:
        time.sleep(60)     # every minute
        scrape_once()
