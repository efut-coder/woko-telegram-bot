# bot.py
import os, time, logging, requests
from threading import Thread
from flask import Flask

# ────────── настройки ──────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292
CHECK_EVERY_SEC = 60                     # частота опроса, сек

CATEGORIES = {
    "zimmer": {
        "url": "https://www.woko.ch/de/zimmer-in-zuerich-details/{}",
        "id":  10203
    },
    "unter": {
        "url": "https://www.woko.ch/de/untermieter-details/{}",
        "id":  10203
    },
    "nach": {
        "url": "https://www.woko.ch/de/nachmieter-details/{}",
        "id":  10210
    },
}

# ────────── helpers ──────────
SENT: set[str] = set()                  # уже отправленные URL

def tg_send(url: str) -> None:
    """Отправка ссылки в Telegram (если ещё не отправляли)."""
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

def url_exists(url: str) -> bool:
    """HEAD-проверка: страница существует?"""
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.status_code == 200
    except requests.RequestException as e:
        logging.warning("HEAD %s: %s", url, e)
        return False

# ────────── watcher ──────────
def watcher() -> None:
    logging.info("watcher start…")

    # 1) шлём стартовые ссылки
    for cat in CATEGORIES.values():
        tg_send(cat["url"].format(cat["id"]))

    # 2) бесконечный опрос
    while True:
        time.sleep(CHECK_EVERY_SEC)

        for name, cat in CATEGORIES.items():
            next_id = cat["id"] + 1
            while url_exists(cat["url"].format(next_id)):
                cat["id"] = next_id            # повышаем максимум
                tg_send(cat["url"].format(next_id))
                next_id += 1                   # ищем ещё выше

# ────────── Flask-заглушка ──────────
app = Flask(__name__)

@app.get("/")
def home():
    return "WOKO-watcher is running"

# ────────── entry ──────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(H:%M:%S)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
