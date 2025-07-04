# bot.py
import os, time, logging, requests, datetime
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup   # pip install beautifulsoup4

# ────────── постоянные параметры ──────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

START_NACHMIETER  = 10198           # начальные «последние известные»
START_UNTERMIETER = 10189
CHECK_EVERY_SEC   = 60              # частота проверки

NACH_URL  = "https://www.woko.ch/en/nachmieter-details/{}"
UNTER_URL = "https://www.woko.ch/en/untermieter-details/{}"

MIN_DATE = datetime.date(2025, 7, 2)   # 02-07-2025

# ────────── Telegram helper ──────────
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

# ────────── проверяем, что страница существует и «свежая» ──────────
def page_is_new(url: str) -> bool:
    """
    True  → страница отдает 200 OK и дата публикации > MIN_DATE
    False → 404/500/старое объявление/не удалось разобрать
    """
    try:
        r = requests.get(url, timeout=15)
    except requests.RequestException as e:
        logging.warning("GET %s: %s", url, e)
        return False

    if r.status_code != 200:
        return False

    # ищем дату в формате 02.07.2025 (на сайте она так выглядит)
    soup = BeautifulSoup(r.text, "html.parser")
    date_tag = soup.find(string=lambda s: s and "." in s and len(s) == 10)
    if not date_tag:
        logging.warning("no date found in %s", url)
        return False

    try:
        day, month, year = map(int, date_tag.split("."))
        pub_date = datetime.date(year, month, day)
    except ValueError:
        logging.warning("cant parse date «%s» in %s", date_tag, url)
        return False

    return pub_date > MIN_DATE

# ────────── главный цикл ──────────
def watcher() -> None:
    nach_id  = START_NACHMIETER
    unter_id = START_UNTERMIETER

    # 1) шлём стартовые ссылки без проверки даты
    tg_send(NACH_URL.format(nach_id))
    tg_send(UNTER_URL.format(unter_id))

    # 2) дальше постоянно ищем id > текущего
    while True:
        time.sleep(CHECK_EVERY_SEC)

        # --- nachmieter ---
        next_nach = nach_id + 1
        while page_is_new(NACH_URL.format(next_nach)):
            tg_send(NACH_URL.format(next_nach))
            nach_id  = next_nach
            next_nach += 1   # проверяем следующие номера без паузы

        # --- untermieter ---
        next_unter = unter_id + 1
        while page_is_new(UNTER_URL.format(next_unter)):
            tg_send(UNTER_URL.format(next_unter))
            unter_id = next_unter
            next_unter += 1

# ────────── Flask-заглушка для Render ──────────
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher is running"

# ────────── entrypoint ──────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    SENT = set()                       # уже отправленные ссылки
    logging.info("Starting watcher…")

    Thread(target=watcher, daemon=True).start()
    # Render отдаёт PORT, локально по 10000
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
