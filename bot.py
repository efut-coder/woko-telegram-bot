# bot.py
import os, time, logging
import requests
from flask import Flask
from threading import Thread

##############################################################################
# 1. НАСТРОЙКИ — ЗАМЕНИТЕ, ЕСЛИ НУЖНО
##############################################################################
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

# стартовые (уже существующие) номера объявлений
START_NACHMIETER = 10198
START_UNTERMIETER = 10189

CHECK_EVERY_SEC = 60  # частота проверки

##############################################################################
# 2. ВСПОМОГАТЕЛЬНЫЕ ШТУКИ
##############################################################################
NACH_FMT = "https://www.woko.ch/en/nachmieter-details/{}"
UNTER_FMT = "https://www.woko.ch/en/untermieter-details/{}"

def tg_send(text: str) -> None:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def url_exists(url: str) -> bool:
    # HEAD хватит, страница отдаёт 404, если не существует
    resp = requests.head(url, allow_redirects=True, timeout=10)
    return resp.status_code == 200

##############################################################################
# 3. ОСНОВНОЙ ЦИКЛ
##############################################################################
def loop() -> None:
    nach_id   = START_NACHMIETER
    unter_id  = START_UNTERMIETER

    # отправляем стартовые ссылки
    tg_send(NACH_FMT.format(nach_id))
    tg_send(UNTER_FMT.format(unter_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # проверяем следующее nachmieter-объявление
        if url_exists(NACH_FMT.format(nach_id + 1)):
            nach_id += 1
            tg_send(NACH_FMT.format(nach_id))

        # проверяем следующее untermieter-объявление
        if url_exists(UNTER_FMT.format(unter_id + 1)):
            unter_id += 1
            tg_send(UNTER_FMT.format(unter_id))

##############################################################################
# 4. FLASK, ЧТОБЫ RENDER НЕ РУГАЛСЯ
##############################################################################
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO watcher running"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Starting watcher…")

    # фоновая нить с циклом
    Thread(target=loop, daemon=True).start()

    # Render слушает порт 10000/0.0.0.0
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
