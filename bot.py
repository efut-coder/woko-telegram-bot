#!/usr/bin/env python3
# coding: utf-8
"""
WOKO-watcher  •  стартовые ссылки + гибридный поиск новинок
"""

import os, time, json, logging, requests, re
from threading import Thread
from flask import Flask
from bs4 import BeautifulSoup
from datetime import datetime, timezone

TOKEN   = os.getenv("TG_TOKEN", "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8")
CHAT_ID = int(os.getenv("TG_CHAT", 194010292))

CHECK_EVERY_SEC = 60
HEAD_GAP_LIMIT  = 5           # сколько подряд 404 увидели – остановить walk

START_LINKS = [
    "https://www.woko.ch/de/zimmer-in-zuerich-details/10203",
    "https://www.woko.ch/de/untermieter-details/10203",
    "https://www.woko.ch/de/nachmieter-details/10210",
]

DETAIL_RX = re.compile(r"/(zimmer-in-zuerich|untermieter|nachmieter)-details/(\d+)$")

# ---------- состояние ----------
sent: set[str] = set()        # уже отправленные URL
last_id: dict[str, int] = {}  # family -> максимальный ID, который мы знаем

# ---------- telegram ----------
def tg_send(url: str) -> None:
    if url in sent:
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": url},
            timeout=10,
        )
        r.raise_for_status()
        sent.add(url)
        logging.info("sent %s", url)
    except Exception as e:
        logging.warning("Telegram send failed %s : %s", url, e)

# ---------- utils ----------
def head_ok(url: str) -> bool:
    try:
        return requests.head(url, allow_redirects=True, timeout=10).status_code == 200
    except requests.RequestException:
        return False

def remember(url: str) -> None:
    m = DETAIL_RX.search(url)
    if not m:
        return
    family, num = m.group(1), int(m.group(2))
    last_id[family] = max(last_id.get(family, 0), num)

# ---------- поиск новинок ----------
def walk_ids() -> None:
    """Перебор ID вперёд до HEAD_GAP_LIMIT подряд 404."""
    for family, current in list(last_id.items()):
        misses = 0
        nxt = current + 1
        while misses < HEAD_GAP_LIMIT:
            probe = f"https://www.woko.ch/de/{family}-details/{nxt}"
            if head_ok(probe):
                tg_send(probe)
                remember(probe)
                misses = 0
            else:
                misses += 1
            nxt += 1

def parse_overview() -> None:
    """Парсинг общей страницы Zimmer in Zürich – подбираем всё, что пропустили."""
    try:
        html = requests.get("https://www.woko.ch/de/zimmer-in-zuerich", timeout=20).text
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("div.inserat a[href]"):
            href = a["href"]
            if DETAIL_RX.search(href):
                full = "https://www.woko.ch" + href
                tg_send(full)
                remember(full)
    except Exception as e:
        logging.warning("overview parse failed: %s", e)

# ---------- главный цикл ----------
def watcher() -> None:
    logging.info("watcher start…")

    # отправляем стартовые ссылки
    for link in START_LINKS:
        tg_send(link)
        remember(link)

    while True:
        walk_ids()        # быстрый HEAD-метод
        parse_overview()  # запасной вариант
        time.sleep(CHECK_EVERY_SEC)

# ---------- Flask (Render пингует /) ----------
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher running — " + datetime.now(timezone.utc).isoformat()

# ---------- запуск ----------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    Thread(target=watcher, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
