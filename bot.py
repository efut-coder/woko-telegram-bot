# bot.py
import os, time, logging, re, requests
from datetime import datetime
from threading import Thread
from bs4 import BeautifulSoup          # pip install beautifulsoup4
from flask import Flask

# ──────────── настройки ────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

START_NACHMIETER  = 10207          # последний увиденный Nachmieter-ID
START_UNTERMIETER = 10189          # последний увиденный Untermieter-ID
CHECK_EVERY_SEC   = 60             # частота опроса страниц (сек.)
MIN_DATE          = datetime(2025, 7, 6)   # «свежесть» объявлений

# Немецкие URL-ы ( /de/ ) — работают и для англ. версии.
NACH_URL  = "https://www.woko.ch/de/nachmieter-details/{}"
UNTER_URL = "https://www.woko.ch/de/untermieter-details/{}"

# ──────────── Telegram ────────────
def tg_send(url: str) -> None:
    if url in SENT:
        return
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": url},
        timeout=15,
    )
    if r.ok:
        SENT.add(url)
        logging.info("sent %s", url)
    else:
        logging.warning("telegram %s → %s", r.status_code, r.text)

# ──────────── сеть ────────────
def head_ok(url: str) -> bool:
    """Проверяем, существует ли страница (HEAD)."""
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.status_code == 200
    except requests.RequestException as e:
        logging.warning("HEAD %s → %s", url, e)
        return False

DATE_RX = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")   # 07.07.2025

def parse_date(html: str) -> datetime | None:
    """Выдёргиваем дату публикации из HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # 1) meta property
    meta = soup.find("meta", {"property": "article:published_time"})
    if meta and meta.get("content"):
        try:
            return datetime.fromisoformat(meta["content"][:10])
        except ValueError:
            pass

    # 2) первый текст «ДД.ММ.ГГГГ»
    m = DATE_RX.search(soup.get_text(" ", strip=True))
    if m:
        d, m_, y = map(int, m.groups())
        return datetime(y, m_, d)

    return None           # дату не нашли → считаем свежим

# ──────────── логика отправки ────────────
def try_send(url: str) -> None:
    if url in SENT:
        return
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return
        pub_date = parse_date(r.text)
        if pub_date and pub_date < MIN_DATE:
            logging.info("skip %s (old %s)", url, pub_date.date())
            return
    except requests.RequestException as e:
        logging.warning("GET %s → %s", url, e)
        return

    tg_send(url)

# ──────────── основной watcher ────────────
def watcher() -> None:
    nach_id, unter_id = START_NACHMIETER, START_UNTERMIETER

    # стартовые ссылки
    try_send(NACH_URL.format(nach_id))
    try_send(UNTER_URL.format(unter_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # Nachmieter
        while head_ok(NACH_URL.format(nach_id + 1)):
            nach_id += 1
            try_send(NACH_URL.format(nach_id))

        # Untermieter
        while head_ok(UNTER_URL.format(unter_id + 1)):
            unter_id += 1
            try_send(UNTER_URL.format(unter_id))

# ──────────── Flask-заглушка для Render ────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher alive"

# ──────────── точка входа ────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    SENT: set[str] = set()

    logging.info("watcher start…")
    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
