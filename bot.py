# bot.py
import os, time, logging, requests
from datetime import datetime
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup     # <-- требует beautifulsoup4 в requirements

TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

START_NACHMIETER  = 10198
START_UNTERMIETER = 10189
CHECK_EVERY_SEC   = 60
MAX_GAP           = 50            # сколько подряд 404 считаем «концом» ленты
DATE_LIMIT        = datetime(2025, 7, 2)

NACH_URL  = "https://www.woko.ch/en/nachmieter-details/{}"
UNTER_URL = "https://www.woko.ch/en/untermieter-details/{}"

SENT: set[str] = set()

# ---------- helpers ----------
def tg_send(url: str) -> None:
    if url in SENT:
        return
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": url},
        timeout=10,
    )
    if r.ok:
        SENT.add(url)
        logging.info("sent %s", url)
    else:
        logging.warning("Telegram error %s → %s", r.status_code, r.text)

def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        logging.warning("GET %s: %s", url, e)
        return None

def is_recent_enough(soup: BeautifulSoup) -> bool:
    time_tag = soup.select_one("time")
    if not time_tag or not time_tag.get("datetime"):
        return False
    published = datetime.fromisoformat(time_tag["datetime"][:10])
    return published >= DATE_LIMIT

def try_send(url: str):
    soup = fetch(url)
    if soup and is_recent_enough(soup):
        tg_send(url)

# ---------- watcher ----------
def watcher() -> None:
    nach_id  = START_NACHMIETER
    unter_id = START_UNTERMIETER

    # отправляем стартовые ссылки
    try_send(NACH_URL.format(nach_id))
    try_send(UNTER_URL.format(unter_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # —–– nachmieter –––
        gap = 0
        while gap < MAX_GAP:
            if fetch(NACH_URL.format(nach_id + 1)):
                nach_id += 1
                gap = 0
                try_send(NACH_URL.format(nach_id))
            else:
                gap += 1
                nach_id += 1

        # —–– untermieter –––
        gap = 0
        while gap < MAX_GAP:
            if fetch(UNTER_URL.format(unter_id + 1)):
                unter_id += 1
                gap = 0
                try_send(UNTER_URL.format(unter_id))
            else:
                gap += 1
                unter_id += 1

# ---------- flask stub ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher is running"

# ---------- entry ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.info("Starting watcher…")
    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
