import time, threading, requests, os
from flask import Flask
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ── Telegram (hard-coded by your request) ─────────────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"

def tg_send(text: str) -> None:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)

# ── Headless Chrome factory ───────────────────────────────────
def make_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}

sent_links: set[str] = set()

def scrape_once():
    drv = make_driver()
    for city, url in PAGES.items():
        try:
            drv.get(url)
            time.sleep(4)
            soup = BeautifulSoup(drv.page_source, "html.parser")
            box = soup.select_one("div.grid-item, div.offer")
            if not box:
                tg_send(f"⚠️  No listings found on WOKO ({city}).")
                continue

            a_tag   = box.find("a", href=True)
            title   = (box.find(["h3", "h2"]) or a_tag).get_text(strip=True)
            full_url = "https://www.woko.ch" + a_tag["href"] if a_tag else url

            if full_url in sent_links:
                continue
            sent_links.add(full_url)

            tg_send(f"🏠 <b>{title}</b>\n🔗 {full_url}\n📍 {city}")
        except Exception as e:
            tg_send(f"❌ Error on {city}: {e}")
    drv.quit()

def bot_loop():
    while True:
        scrape_once()
        time.sleep(60)          # every minute

# ── Flask keep-alive ──────────────────────────────────────────
app = Flask(__name__)
@app.route("/")
def home(): return "✅ WOKO bot is running"

# ── Start everything ─────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Bot starting …")
    threading.Thread(target=bot_loop, daemon=True).start()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=False)
