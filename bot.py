# bot.py  (python 3.8+)
import os, time, logging, re, requests
from datetime import datetime
from threading import Thread
from bs4 import BeautifulSoup          # requirements.txt → beautifulsoup4
from flask import Flask

TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

MIN_NACH = 10198          # числа-стартеры
MIN_UNTER = 10189
MIN_DATE  = datetime(2025, 7, 2)        # 02 июля 2025  🚦

CHECK_EVERY_SEC = 60
LANGS = ("en", "de")                    # теперь проверяем оба раздела

BASE = "https://www.woko.ch/{lang}/{kind}-details/{id}"
KINDS = {
    "nach": ("nachmieter",  MIN_NACH ),
    "unter": ("untermieter", MIN_UNTER)
}

SENT = set()                            # что уже отправляли

# ---------- helpers ----------
def tg_send(url: str) -> None:
    if url in SENT:           # не дублируем
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

def page_ok(url: str) -> tuple[bool, str]:
    "HEAD-проверка + возвращает финальный URL (учёт редиректа)"
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.status_code == 200, r.url
    except requests.RequestException:
        return False, url

DATE_RX = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})")   # 04.07.2025

def recent_enough(url: str) -> bool:
    "Скачивает страницу, вытаскивает первую дату в формате dd.MM.yyyy"
    try:
        html = requests.get(url, timeout=10).text
        m = DATE_RX.search(html)
        if not m:
            logging.warning("no date %s", url);  return False
        d = datetime(int(m[3]), int(m[2]), int(m[1]))
        return d >= MIN_DATE
    except requests.RequestException as e:
        logging.warning("GET %s: %s", url, e)
        return False

def try_send(kind: str, id_: int) -> None:
    slug, _ = KINDS[kind]
    for lang in LANGS:
        url = BASE.format(lang=lang, kind=slug, id=id_)
        ok, final = page_ok(url)
        if ok and recent_enough(final):
            tg_send(final)
            break                           # если нашли в одном языке – достаточно

# ---------- watcher ----------
def watcher() -> None:
    # стартовые ссылки
    for kind, (_, start) in KINDS.items():
        try_send(kind, start)

    id_cur = {k: start for k, (_, start) in KINDS.items()}

    while True:
        time.sleep(CHECK_EVERY_SEC)
        for kind, (_, _) in KINDS.items():
            nxt = id_cur[kind] + 1
            while True:
                try_send(kind, nxt)
                if nxt in SENT:             # страница есть и прошла оба фильтра
                    id_cur[kind] = nxt       # сдвигаем «текущий максимум»
                    nxt += 1
                else:                       # как только HEAD→404 – стоп цикла
                    break

# ---------- flask stub ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher running"

# ---------- entry ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.info("Starting watcher…")
    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
