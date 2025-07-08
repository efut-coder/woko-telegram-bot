#!/usr/bin/env python3
# bot.py

import json
import logging
import os
import time
from pathlib import Path
from threading import Thread

import requests
from flask import Flask

# ---------- настройки ----------
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

CHECK_EVERY_SEC = 60          # как часто пробовать +1

START_ZH_ID   = 10203         # /zimmer-in-zuerich-details/
START_UNTER_ID = 10203        # /untermieter-details/
START_NACH_ID  = 10210        # /nachmieter-details/

ZH_URL   = "https://www.woko.ch/de/zimmer-in-zuerich-details/{}"
UNTER_URL = "https://www.woko.ch/de/untermieter-details/{}"
NACH_URL  = "https://www.woko.ch/de/nachmieter-details/{}"

SENT_FILE = Path("sent.json")   # здесь храним уже отосланные ссылки
SENT: set[str] = set()

# ---------- утилиты ----------
def load_sent() -> None:
    if SENT_FILE.exists():
        try:
            SENT.update(json.loads(SENT_FILE.read_text()))
        except Exception:
            logging.warning("Не смог прочитать %s, начинаю с пустого списка", SENT_FILE)

def save_sent() -> None:
    try:
        SENT_FILE.write_text(json.dumps(list(SENT), indent=2))
    except Exception as e:
        logging.warning("Не смог сохранить %s: %s", SENT_FILE, e)

def norm_url(url: str) -> str:
    """канонизируем для set() – регистр и завершающий слэш не важны"""
    return url.lower().rstrip('/')

def tg_send(url: str) -> None:
    u = norm_url(url)
    if u in SENT:
        return          # уже отправляли

    ok = False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": url},
            timeout=15,
        )
        ok = r.ok
    except requests.RequestException as e:
        logging.warning("Telegram error: %s", e)

    if ok:
        SENT.add(u)
        save_sent()
        logging.info("sent %s", url)
    else:
        logging.warning("Не удалось отправить %s", url)

def url_exists(url: str) -> bool:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        return False

# ---------- основной цикл ----------
def watcher() -> None:
    logging.info("watcher start…")
    # загрузили историю
    load_sent()

    # текущие max-ID
    zh_id, unter_id, nach_id = START_ZH_ID, START_UNTER_ID, START_NACH_ID

    # шлём стартовые ссылки (они запишутся в SENT и больше не повторятся)
    tg_send(ZH_URL.format(zh_id))
    tg_send(UNTER_URL.format(unter_id))
    tg_send(NACH_URL.format(nach_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # zimmer-in-zuerich
        while url_exists(ZH_URL.format(zh_id + 1)):
            zh_id += 1
            tg_send(ZH_URL.format(zh_id))

        # untermieter
        while url_exists(UNTER_URL.format(unter_id + 1)):
            unter_id += 1
            tg_send(UNTER_URL.format(unter_id))

        # nachmieter
        while url_exists(NACH_URL.format(nach_id + 1)):
            nach_id += 1
            tg_send(NACH_URL.format(nach_id))

# ---------- Flask заглушка для Render ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO watcher up & running"

# ---------- entrypoint ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    Thread(target=watcher, daemon=True).start()
    # Render передаёт порт через переменную окружения PORT
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
