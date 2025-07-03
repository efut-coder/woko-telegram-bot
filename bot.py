# bot.py  ─────────────────────────────────────────────────────
# WOKO watcher: отслеживаем монотонный рост двух ID на сайте
#   https://www.woko.ch/en/nachmieter-details/<id>
#   https://www.woko.ch/en/untermieter-details/<id>
# без Selenium, только requests.

import threading, time, logging, html, requests
from flask import Flask, Response

# ──────────────── Telegram credentials ────────────────
TOKEN  = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHATID = "194010292"

def tg_send(msg: str) -> None:
    """Отправка сообщения в Telegram с минимальной обработкой ошибок."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHATID, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logging.warning("Telegram send failed: %s", e)

# ──────────────── Константы и стартовые ID ────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (WOKO-watcher/1.0)"}

NACH_BASE   = "https://www.woko.ch/en/nachmieter-details/{}"
UNTER_BASE  = "https://www.woko.ch/en/untermieter-details/{}"

last_nach   = 10198  # уже существует → шлём сразу, потом ждём 10199…
last_unter  = 10189  #                → шлём сразу, потом ждём 10190…

def url_exists(url: str) -> bool:
    """True, если страница реально есть (код 200 и не 404-текст внутри)."""
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return False
    lt = r.text.lower()
    return ("page could not be found" not in lt) and ("not been found" not in lt)

def announce(url: str) -> None:
    tg_send(f"🏠 <a href=\"{html.escape(url)}\">{html.escape(url)}</a>")

# ──────────────── Основной цикл ────────────────
def poll_loop() -> None:
    global last_nach, last_unter
    # 1. присылаем стартовые ссылки
    announce(NACH_BASE.format(last_nach))
    announce(UNTER_BASE.format(last_unter))

    while True:
        # Проверяем nachmieter
        next_nach = last_nach + 1
        if url_exists(NACH_BASE.format(next_nach)):
            last_nach = next_nach
            announce(NACH_BASE.format(last_nach))
            continue  # сразу ищем ещё, без паузы

        # Проверяем untermieter
        next_unter = last_unter + 1
        if url_exists(UNTER_BASE.format(next_unter)):
            last_unter = next_unter
            announce(UNTER_BASE.format(last_unter))
            continue  # сразу ищем ещё

        # Если ничего нового, ждём минуту
        time.sleep(60)

# ──────────────── Flask для “живости” на Render ────────────────
app = Flask(__name__)

@app.route("/")
def root() -> Response:                 # health-check
    return Response("✅ WOKO watcher running", 200)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    threading.Thread(target=poll_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
