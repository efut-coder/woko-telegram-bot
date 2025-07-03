"""
WOKO → Telegram  (requests-only, no Selenium)
"""
import os, time, threading, requests
from flask import Flask
from bs4 import BeautifulSoup

# ── Telegram (hard-coded) ─────────────────────────────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"
def tg(msg: str):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
                  timeout=8)

# ── Pages to watch ────────────────────────────────────────────
PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}

sent: set[str] = set()        # duplicate filter

def scrape_once():
    headers = {"User-Agent": "Mozilla/5.0"}   # mimic browser
    for city, url in PAGES.items():
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            soup  = BeautifulSoup(r.text, "html.parser")

            # WOKO listings appear as div.row.offer  (primary)  or div.grid-item (fallback)
            boxes = soup.select("div.row.offer") or soup.select("div.grid-item")
            print(f"▶ {city}: FOUND {len(boxes)} boxes")

            if not boxes:
                tg(f"⚠️  No listings found on WOKO ({city}).")
                continue

            first   = boxes[0]
            a_tag   = first.find("a", href=True)
            title   = (first.find(["h3","h2"]) or a_tag).get_text(strip=True)
            fullurl = "https://www.woko.ch" + a_tag["href"] if a_tag else url

            if fullurl in sent:
                continue
            sent.add(fullurl)

            tg(f"🏠 <b>{title}</b>\n🔗 {fullurl}\n📍 {city}")

        except Exception as e:
            tg(f"❌ {city}: {e}")
            print("ERR:", city, e)

def worker():
    i = 0
    while True:
        print(f"HB {i}")
        scrape_once()
        i += 1
        time.sleep(60)

# ── Flask keep-alive for Render ───────────────────────────────
app = Flask(__name__)
@app.route("/")
def root(): return "✅ WOKO bot is running"

if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=False)

