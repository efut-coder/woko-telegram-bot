# bot.py – 100 % requests/BS4 solution, no Selenium needed

TOKEN  = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHATID = "194010292"

import time, logging, threading, html
from typing import List, Tuple, Optional

import requests
from bs4 import BeautifulSoup
from flask import Flask, Response

# ───────────────────────── Telegram ──────────────────────────
def tg_send(text: str) -> None:
    """Send a Telegram message with basic error handling."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHATID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as exc:
        logging.warning("Telegram send failed: %s", exc)

# ────────────────────────── Scraper ──────────────────────────
PAGES: List[Tuple[str, str]] = [
    ("Zürich",               "https://www.woko.ch/de/zimmer-in-zuerich"),
    ("Winterthur/Wädenswil", "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil"),
    ("Wädenswil",            "https://www.woko.ch/de/zimmer-in-waedenswil"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WOKO-bot/1.0; +https://github.com/efut-coder)"
}

def fetch(url: str) -> str:
    """Download a page and return its HTML text."""
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

def extract_first_listing(html_text: str) -> Optional[Tuple[str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")
    card = soup.select_one("div.grid-item")
    if not card:
        return None
    title = card.find("h3").get_text(strip=True)
    link  = "https://www.woko.ch" + card.find("a")["href"]
    return title, link

def scrape_once() -> None:
    for name, url in PAGES:
        logging.info("GET %s …", name)
        try:
            html_text = fetch(url)
            # The “Free rooms” tab is rendered as a separate HTML block right in the page,
            # so simply re-parsing the full page works – no click needed.
            res = extract_first_listing(html_text)
            if res is None:
                tg_send(f"⚠️ Kein Inserat für <b>{html.escape(name)}</b>")
                continue
            title, link = res
            tg_send(f"🏠 <b>{html.escape(title)}</b>\n🔗 {link}")
        except Exception as exc:
            logging.exception("Error while scraping %s: %s", name, exc)
            tg_send(f"❌ Fehler bei <b>{html.escape(name)}</b>:\n<code>{html.escape(str(exc))}</code>")

# ────────────────── Background loop + Flask app ──────────────
app = Flask(__name__)

@app.route("/")
def root() -> Response:
    return Response("✅ WOKO bot (requests edition) is running", 200)

def loop() -> None:
    beat = 0
    while True:
        logging.info("HB %d", beat)
        beat = (beat + 1) % 60
        scrape_once()
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
