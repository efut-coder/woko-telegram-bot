# bot.py
import os, time, logging, requests
from datetime import datetime
from threading import Thread
from typing import Set, Optional
from bs4 import BeautifulSoup
from flask import Flask

# ──────── настройка ────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

START_NACHMIETER  = 10207
START_UNTERMIETER = 10189
CHECK_EVERY_SEC   = 60                       # частота опроса
MIN_DATE          = datetime(2025, 7, 6)     # 06-07-2025

NACH_URL  = "https://www.woko.ch/de/nachmieter-details/{}"
UNTER_URL = "https://www.woko.ch/de/untermieter-details/{}"

# ──────── helpers ────────
def tg_send(url: str, sent: Set[str]) -> None:
    """Отправить ссылку в Telegram (один раз)."""
    if url in sent:
        return
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": url},
        timeout=10,
    )
    if r.ok:
        sent.add(url)
        logging.info("sent %s", url)
    else:
        logging.warning("TG error %s → %s", r.status_code, r.text)

def page_date(html: str) -> Optional[datetime]:
    """Вытащить дату из <time datetime="YYYY-MM-DD"> либо из текста вида 06.07.2025."""
    soup = BeautifulSoup(html, "html.parser")

    # вариант с тегом <time datetime="2025-07-06">
    t = soup.find("time", attrs={"datetime": True})
    if t and t["datetime"]:
        try:
            return datetime.strptime(t["datetime"][:10], "%Y-%m-%d")
        except ValueError:
            pass

    # fallback: дата встречается как текст 06.07.2025
    for txt in soup.stripped_strings:
        if "." in txt and len(txt) == 10:
            try:
                return datetime.strptime(txt, "%d.%m.%Y")
            except ValueError:
                continue
    return None            # ничего не нашли

def is_recent_enough(url: str) -> bool:
    """HEAD + GET: проверяем, существует ли страница и не старше ли она 06-07-25."""
    try:
        h = requests.head(url, allow_redirects=True, timeout=10)
        if h.status_code != 200:
            return False
    except requests.RequestException:
        return False

    try:
        g = requests.get(url, timeout=10)
        if g.status_code != 200:
            return False
        dt = page_date(g.text) or datetime.min
        return dt >= MIN_DATE
    except requests.RequestException as e:
        logging.warning("GET %s: %s", url, e)
        return False

# ──────── watcher ────────
def watcher() -> None:
    sent: Set[str] = set()

    nach_id  = START_NACHMIETER
    unter_id = START_UNTERMIETER

    # 1️⃣ шлём стартовые ссылки (дата не проверяется)
    tg_send(NACH_URL.format(nach_id),  sent)
    tg_send(UNTER_URL.format(unter_id), sent)

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # nachmieter
        while True:
            nxt = nach_id + 1
            url = NACH_URL.format(nxt)
            if not is_recent_enough(url):
                break
            nach_id = nxt
            tg_send(url, sent)

        # untermieter
        while True:
            nxt = unter_id + 1
            url = UNTER_URL.format(nxt)
            if not is_recent_enough(url):
                break
            unter_id = nxt
            tg_send(url, sent)

# ──────── Flask stub ────────
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher running"

# ──────── entry ────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.info("Starting watcher…")
    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
