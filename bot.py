# bot.py  —  минимальный “URL-watcher” без дублей
import os, time, logging, requests
from threading import Thread
from flask import Flask

TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

START_NACHMIETER   = 10198      # последние актуальные id на момент запуска
START_UNTERMIETER  = 10189
CHECK_EVERY_SEC    = 60         # частота проверки

NACH_FMT   = "https://www.woko.ch/en/nachmieter-details/{}"
UNTER_FMT  = "https://www.woko.ch/en/untermieter-details/{}"

# ----------------------- helpers -----------------------
def tg_send(url: str) -> None:
    if url in SENT:                         # уже отправляли → пропускаем
        return
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": url})
    if r.ok:
        SENT.add(url)
    else:
        logging.warning("Telegram error %s → %s", r.status_code, r.text)

def url_exists(url: str) -> bool:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.status_code == 200
    except requests.RequestException as e:
        logging.warning("HEAD %s failed: %s", url, e)
        return False

# ----------------------- main loop ---------------------
def loop() -> None:
    nach_id  = START_NACHMIETER
    unter_id = START_UNTERMIETER

    # стартовые ссылки
    tg_send(NACH_FMT.format(nach_id))
    tg_send(UNTER_FMT.format(unter_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        nxt = nach_id + 1
        if url_exists(NACH_FMT.format(nxt)):
            nach_id = nxt
            tg_send(NACH_FMT.format(nach_id))

        nxt = unter_id + 1
        if url_exists(UNTER_FMT.format(nxt)):
            unter_id = nxt
            tg_send(UNTER_FMT.format(unter_id))

# ----------------------- flask stub --------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO watcher running"

# ----------------------- entrypoint --------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    SENT = set()                                # <— здесь храним уже высланные URL
    logging.info("Starting watcher…")

    Thread(target=loop, daemon=True).start()    # фоновая проверка
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
