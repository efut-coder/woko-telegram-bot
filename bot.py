"""
Minimal WOKO → Telegram bot
‒ no python-telegram-bot import
‒ keeps Render alive by running Flask on PORT (default 8080)
"""

import os, time, threading, requests
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# ── 1.  YOUR TELEGRAM CREDENTIALS (hard-coded) ───────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"

def tg(text: str) -> None:
    """Send plain HTML to Telegram via one HTTP POST."""
    api = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(api, data={"chat_id": CHAT_ID,
                             "text": text,
                             "parse_mode": "HTML"},
                  timeout=10)

# ── 2.  Selenium helper ──────────────────────────────────────
def make_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

# ── 3.  Pages to watch (German) ──────────────────────────────
PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}

sent: set[str] = set()        # duplicate filter

def scrape_once():
    drv = make_driver()

    for city, url in PAGES.items():
        try:
            drv.get(url)

            # click cookie banner if visible (text “Alle akzeptieren” OR “Accept all”)
            try:
                btn = WebDriverWait(drv, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'akzeptieren') or contains(.,'Accept all')]")
                    )
                )
                btn.click()
            except Exception:
                pass

            # wait until at least one <div class*="offer"> appears (max 15 s)
            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'offer')]"))
            )
        except Exception as e:
            tg(f"❌ {city}: Seite lädt nicht ({e})")
            continue

        # parse page source
        soup  = BeautifulSoup(drv.page_source, "html.parser")
        boxes = soup.select("div.offer")                # main listing blocks

        if not boxes:
            tg(f"❓ Found 0 elements on {city} – selector still wrong?")
            continue

        first = boxes[0]
        a_tag = first.find("a", href=True)
        title = (first.find(["h3","h2"]) or a_tag).get_text(strip=True)
        link  = "https://www.woko.ch" + a_tag["href"] if a_tag else url

        if link in sent:
            continue
        sent.add(link)

        tg(f"🏠 <b>{title}</b>\n🔗 {link}\n📍 {city}")

    drv.quit()

# ── 4.  background loop every 60 s ───────────────────────────
def worker():
    while True:
        scrape_once()
        time.sleep(60)

# ── 5.  Flask – keeps Render Web Service alive ───────────────
app = Flask(__name__)
@app.route("/")
def root(): return "✅ WOKO bot is running"

if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=False)
