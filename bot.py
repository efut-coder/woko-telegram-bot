# bot.py
import os, time, logging, requests
from threading import Thread
from flask import Flask

TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

START_NACHMIETER  = 10198          # начальный максимум
START_UNTERMIETER = 10189
CHECK_EVERY_SEC   = 60

NACH_URL  = "https://www.woko.ch/en/nachmieter-details/{}"
UNTER_URL = "https://www.woko.ch/en/untermieter-details/{}"

# ---------- helpers ----------
def tg_send(url: str) -> None:
    if url in SENT:                      # уже отправляли?
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

def url_ok(url: str) -> bool:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.status_code == 200
    except requests.RequestException as e:
        logging.warning("HEAD %s: %s", url, e)
        return False

# ---------- watcher ----------
def watcher() -> None:
    nach_id  = START_NACHMIETER
    unter_id = START_UNTERMIETER

    # отправляем стартовые ссылки
    tg_send(NACH_URL.format(nach_id))
    tg_send(UNTER_URL.format(unter_id))

    while True:
        time.sleep(CHECK_EVERY_SEC)

        # —–– nachmieter –––
        while url_ok(NACH_URL.format(nach_id + 1)):
            nach_id += 1
            tg_send(NACH_URL.format(nach_id))

        # —–– untermieter –––
        while url_ok(UNTER_URL.format(unter_id + 1)):
            unter_id += 1
            tg_send(UNTER_URL.format(unter_id))

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
    SENT = set()                       # здесь храним уже отправленные URL
    logging.info("Starting watcher…")

    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
