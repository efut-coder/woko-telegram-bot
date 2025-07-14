#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WOKO watcher: парсит агрегатор /zimmer-in-zuerich, присылает новые ссылки в Telegram.
Работает как web-service на Render: запускает Flask (порт для Render) + фоновую нить-парсер.
"""

import os
import json
import time
import threading
import logging
from typing import List, Set

import requests
from flask import Flask
from bs4 import BeautifulSoup

# --------------------- НАСТРОЙКИ --------------------------------------------
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = 194010292              # Your personal Telegram ID
FAMILY_GROUP_ID = -1004843343749 # Your Family group chat ID ✅

LIST_URL        = "https://woko.ch/de/zimmer-in-zuerich"
CHECK_EVERY_SEC = 30
VIEWED_FILE     = "viewed.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WOKO-watcher/1.0)"
}

# --------------------- Telegram ---------------------------------------------
def tg_send(text: str, chat_id: int = CHAT_ID) -> None:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    if r.ok:
        logging.info("sent to %s: %s", chat_id, text)
    else:
        logging.warning("Telegram error %s → %s", r.status_code, r.text)

# --------------------- парсер страницы --------------------------------------
def fetch_listing() -> List[str]:
    r = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    links: List[str] = []

    for div in soup.find_all("div", class_="inserat"):
        a = div.find("a", href=True)
        if a:
            links.append(a["href"].strip())

    return links

# --------------------- utils -------------------------------------------------
def load_viewed() -> Set[str]:
    if os.path.exists(VIEWED_FILE):
        with open(VIEWED_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_viewed(viewed: Set[str]) -> None:
    with open(VIEWED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(viewed), f, indent=2)

# --------------------- watcher thread ---------------------------------------
def watcher() -> None:
    viewed = load_viewed()
    logging.info("watcher start… cached %d links", len(viewed))

    # --- Send the newest listing once for testing ---
    try:
        latest = fetch_listing()[0]  # most recent listing
        abs_url = f"https://woko.ch{latest}"
        tg_send(abs_url)                               # send to you
        tg_send(abs_url, chat_id=FAMILY_GROUP_ID)      # send to family group ✅
        viewed.add(latest)
    except Exception:
        logging.exception("initial test send failed")
    # ------------------------------------------------

    while True:
        try:
            new_links = fetch_listing()
            for href in new_links:
                if href in viewed:
                    continue
                abs_url = f"https://woko.ch{href}"
                tg_send(abs_url)                               # send to you
                tg_send(abs_url, chat_id=FAMILY_GROUP_ID)      # send to family group ✅
                viewed.add(href)

            save_viewed(viewed)

        except Exception as exc:  # noqa: BLE001
            logging.exception("fetch failed: %s", exc)

        time.sleep(CHECK_EVERY_SEC)

# --------------------- Flask stub for Render --------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "WOKO-watcher alive"

# --------------------- entry ------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    threading.Thread(target=watcher, daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
