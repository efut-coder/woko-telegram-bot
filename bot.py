import os, re, time, logging, requests
from datetime import datetime
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup     # ← новая зависимость

TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

# с этих номеров начинаем
START_NACHMIETER  = 10207
START_UNTERMIETER = 10189

DATE_LIMIT = datetime(2025, 7, 6)        # ≥ 06.07.2025
CHECK_EVERY_SEC = 60                     # частота опроса
LOOKAHEAD       = 20                     # насколько далеко заглядываем вперёд

BASE_NACH = "https://www.woko.ch/de/nachmieter-details/{}"
BASE_UNT  = "https://www.woko.ch/de/untermieter-details/{}"

# ────────── helpers ──────────
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
        logging.warning("TG error %s → %s", r.status_code, r.text)

def page_date(url: str) -> datetime | None:
    """
    Скачиваем страницу, ищем первую дату вида 30.06.2025.
    Возвращаем datetime или None, если дата не найдена.
    """
    try:
        html = requests.get(url, timeout=10).text
    except requests.RequestException as e:
        logging.warning("GET %s: %s", url, e)
        return None

    soup = BeautifulSoup(html, "html.parser")
    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", soup.get_text())
    if not m:
        logging.warning("no date on %s", url)
        return None

    try:
        return datetime.strptime(m.group(1), "%d.%m.%Y")
    except ValueError:
        return None

def try_send(url: str) -> bool:
    """
    Возвращает True, если ссылка существует (status 200).
    Отправляет в TG только когда дата ≥ DATE_LIMIT.
    """
    try:
        if requests.head(url, allow_redirects=True, timeout=10).status_code != 200:
            return False
    except requests.RequestException:
        return False

    d = page_date(url)
    if d and d >= DATE_LIMIT:
        tg_send(url)
    return True        # страница существует независимо от даты

# ────────── watcher ──────────
def watcher() -> None:
    nach_id  = START_NACHMIETER
    unt_id   = START_UNTERMIETER

    while True:
        # nachmieter
        for i in range(1, LOOKAHEAD + 1):
            url = BASE_NACH.format(nach_id + i)
            if try_send(url):
                nach_id += i

        # untermieter
        for i in range(1, LOOKAHEAD + 1):
            url = BASE_UNT.format(unt_id + i)
            if try_send(url):
                unt_id += i

        time.sleep(CHECK_EVERY_SEC)

# ────────── flask stub ──────────
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO watcher is running"

# ────────── entry ──────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(H:%M:%S) %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    SENT: set[str] = set()
    logging.info("Starting watcher…")
    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
