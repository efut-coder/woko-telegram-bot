"""
WOKO watcher – plain HTTP to Telegram
─────────────────────────────────────
Render service type : Web Service
Start command       : gunicorn bot:app --bind 0.0.0.0:${PORT:-8080}
"""

import time, threading, requests
from flask import Flask
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ── Telegram credentials (hard-coded at your request) ──────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"

def tg_send(text: str) -> None:
    """Send an HTML-formatted Telegram message via plain HTTP POST."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as exc:
        print("⚠️  Telegram send error:", exc)

# ── Selenium headless Chrome factory ───────────────────────────
def make_driver():
    opt = Options()
    opt.add_argument("--headless")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opt)

# ── WOKO pages to watch ────────────────────────────────────────
PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}

sent_links: set[str] = set()        # duplicate filter

def scan_once() -> None:
    drv = make_driver()

    for city, url in PAGES.items():
        print(f"🔎  Checking {city}")
        try:
            drv.get(url)
            time.sleep(4)                   # allow JS to render

            soup = BeautifulSoup(drv.page_source, "html.parser")
            box  = soup.select_one("div.grid-item, div.offer")
            if not box:
                print(f"⚠️  No listings on {city}")
                tg_send(f"⚠️  No listings found on WOKO ({city}).")
                continue

            link_tag  = box.find("a", href=True)
            title_tag = box.find(["h3", "h2"])

            full_link = ("https://www.woko.ch" + link_tag["href"]) if link_tag else url
            title     = title_tag.get_text(strip=True) if title_tag else "Kein Titel"

            if full_link in sent_links:
                print("• already sent")
                continue

            sent_links.add(full_link)
            msg = f"🏠 <b>{title}</b>\n🔗 {full_link}\n📍 {city}"
            tg_send(msg)
            print("✅ sent")

        except Exception as e:
            err = f"❌ Error on {city}: {e}"
            print(err)
            tg_send(err)

    drv.quit()

def loop_forever():
    while True:
        scan_once()
        time.sleep(60)          # every minute

# ── Flask keep-alive app ───────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def root():
    return "✅ WOKO bot is running"

# ── Start background thread then hand control to gunicorn ─────
def _starter():
    t = threading.Thread(target=loop_forever, daemon=True)
    t.start()
    print("🤖 Bot loop started in background")

_starter()       # fire it once at import-time so gunicorn sees it
