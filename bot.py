# bot.py
import os
import time
import logging
import requests
from datetime import datetime
from threading import Thread
from typing import Final, Set

from bs4 import BeautifulSoup      # pip install beautifulsoup4
from flask import Flask

# ───── настройки Telegram ─────
TOKEN:   Final[str]  = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID: Final[int]  = 194010292

# ───── начальные ID и язык URL ─────
START_NACH:  Final[int] = 10198        # последняя известная Nachmieter
START_UNTER: Final[int] = 10189        # последняя известная Untermieter
LANG_PATH:   Final[str] = "de"         # "de" или "en" – язык в ссылке

# ───── фильтр по дате ─────
MIN_DATE: Final[datetime] = datetime(2025, 7, 6)   # ≥ 06-07-2025

# ───── частота проверки ─────
CHECK_EVERY_SEC: Final[int] = 60

# ───── URL-шаблоны ─────
NACH_URL  = f"https://www.woko.ch/{LANG_PATH}/nachmieter-details/{{}}"
UNTER_URL = f"https://www.woko.ch/{LANG_PATH}/untermieter-details/{{}}"

# ───── глобальное множество отправленных ссылок ─────
SENT: Set[str] = set()

# ---------- helpers ----------
def tg_send(url: str) -> None:
    """Отправить ссылку в Telegram (если ещё не отправляли)."""
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


def extract_date(html: str) -> datetime | None:
    """Вытащить дату публикации с страницы WOKO.  
    Ожидаемый формат в HTML: <time ...>07.07.2025</time>
    """
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("time")
    if not tag or not tag.get_text(strip=True):
        return None

    try:
        # даты на сайте в формате DD.MM.YYYY
        return datetime.strptime(tag.get_text(strip=True), "%d.%m.%Y")
    except ValueError:
        return None


def try_send(url: str) -> bool:
    """Скачать страницу, проверить дату, при необходимости отправить.
    Возвращает True, если страница существует; False – если 404-нет.
    """
    try:
        resp = requests.get(url, timeout=10)
    except requests.RequestException as e:
        logging.warning("GET %s: %s", url, e)
        return False

    if resp.status_code == 404:
        return False

    if resp.status_code != 200:
        logging.warning("GET %s → %s", url, resp.status_code)
        return True          # страница есть, но странный код – пропускаем без отправки

    # ─── фильтр по дате ───
    pub_date = extract_date(resp.text)
    if pub_date and pub_date >= MIN_DATE:
        tg_send(url)
    else:
        logging.debug("skip %s (date %s too old)", url, pub_date)

    return True


# ---------- watcher ----------
def watcher() -> None:
    nach_id  = START_NACH
    unter_id = START_UNTER

    # стартовые ссылки всегда отправляем
    try_send(NACH_URL.format(nach_id))
    try_send(UNTER_URL.format(unter_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # —–– Nachmieter –––
        while True:
            next_id = nach_id + 1
            if not try_send(NACH_URL.format(next_id)):
                break           # не существует – выходим из while
            nach_id = next_id   # страница была, сдвигаем окно

        # —–– Untermieter –––
        while True:
            next_id = unter_id + 1
            if not try_send(UNTER_URL.format(next_id)):
                break
            unter_id = next_id


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
    # Render даёт переменную PORT, локально используем 10000
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
