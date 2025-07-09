#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WOKO watcher  – “внешний” парсинг списка объявлений
(1) загружает страницу /zimmer-in-zuerich
(2) ищет все <div class="inserat"> -> <a href="…">
(3) если ссылки нет в viewed.json – шлёт её в Telegram
"""

import os
import json
import time
import logging
from typing import List, Set

import requests
from bs4 import BeautifulSoup


# ---------- НАСТРОЙКИ --------------------------------------------------------
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292

LIST_URL = "https://woko.ch/de/zimmer-in-zuerich"   # нем. версия; можно заменить на /en/
CHECK_EVERY_SEC = 60

VIEWED_FILE = "viewed.json"           # локальное хранилище уже отправленных href

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WOKO-watcher/1.0; "
        "+https://github.com/efut-coder/woko-telegram-bot)"
    )
}


# ---------- Telegram ---------------------------------------------------------
def tg_send(text: str) -> None:
    """Отправить сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    if not r.ok:
        logging.warning("Telegram error %s → %s", r.status_code, r.text)
    else:
        logging.info("sent %s", text)


# ---------- парсер списка ----------------------------------------------------
def fetch_listing() -> List[str]:
    """Вернуть список href (относительных) из блока inserat"""
    r = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    links: List[str] = []

    for div in soup.find_all("div", class_="inserat"):
        a = div.find("a", href=True)
        if not a:
            continue
        links.append(a["href"])  # '/de/zimmer-in-zuerich-details/10210' и т.д.

    return links


# ---------- основная петля ---------------------------------------------------
def load_viewed() -> Set[str]:
    if os.path.exists(VIEWED_FILE):
        with open(VIEWED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_viewed(viewed: Set[str]) -> None:
    with open(VIEWED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(viewed), f, indent=2)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(H:%M:%S)s %(levelname)s %(message)s",  # только время
    )

    viewed = load_viewed()
    logging.info("watcher started, already have %d links", len(viewed))

    # --- отправляем стартовый список (внешний парсер сразу всё увидит) -------
    try:
        for href in fetch_listing():
            abs_url = f"https://woko.ch{href}"
            if href not in viewed:
                tg_send(abs_url)
                viewed.add(href)
        save_viewed(viewed)
        logging.info("initial dump sent (%d links)", len(viewed))
    except Exception as exc:  # noqa: BLE001
        logging.exception("initial fetch failed: %s", exc)

    # --- основной цикл -------------------------------------------------------
    while True:
        time.sleep(CHECK_EVERY_SEC)
        try:
            for href in fetch_listing():
                if href in viewed:
                    continue
                abs_url = f"https://woko.ch{href}"
                tg_send(abs_url)
                viewed.add(href)

            save_viewed(viewed)

        except Exception as exc:  # noqa: BLE001
            logging.exception("fetch failed: %s", exc)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
