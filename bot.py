import os, time, threading, requests, re
from flask import Flask
from bs4 import BeautifulSoup

# ───────────────── Telegram ───────────────────────────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"
def tg(msg: str):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
                  timeout=8)

# ───────────────── Pages to watch ─────────────────────────────
PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}

sent : set[str] = set()

UA = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "de,en;q=0.9"
}

SELECTORS = [
    "div.row.offer",        # original
    "div.offer",            # alternative
    "div.offer-teaser",     # found on some pages
    "div.grid-item",        # front-page grid boxes
]

def find_boxes(soup: BeautifulSoup):
    """Try several selectors, return first non-empty list (or [])."""
    for sel in SELECTORS:
        boxes = soup.select(sel)
        if boxes:
            return boxes, sel
    return [], None

# ───────────────── scrape & notify once ───────────────────────
def scrape_once():
    for city, url in PAGES.items():
        try:
            print(f"GET {city} …")
            r = requests.get(url, headers=UA, timeout=10)
            r.raise_for_status()

            soup   = BeautifulSoup(r.text, "html.parser")
            boxes, sel = find_boxes(soup)

            if not boxes:
                # Fallback: any <a> with "/zimmer-" in href
                links = [a for a in soup.find_all("a", href=True)
                         if "/zimmer-" in a["href"]][:10]
                if links:
                    boxes = links    # treat anchors as 'boxes'
                    sel   = "<a/href>"
            print(f"▶ {city}: {len(boxes)} boxes (selector: {sel})")

            if not boxes:
                tg(f"DBG: Kein Treffer in {city}. Selector = {sel or 'NONE'}")
                continue

            first   = boxes[0]
            # If we fell back to anchors, first IS an <a>
            a_tag   = first if first.name == "a" else first.find("a", href=True)
            title   = (first.get_text(" ", strip=True)[:120]
                       if first else "Kein Titel")
            link    = ("https://www.woko.ch" + a_tag["href"]
                       if a_tag and a_tag["href"].startswith("/")
                       else (a_tag["href"] if a_tag else url))

            if link in sent:
                continue
            sent.add(link)

            tg(f"🏠 <b>{title}</b>\n🔗 {link}\n📍 {city}")

        except Exception as e:
            print("ERR:", city, e)
            tg(f"❌ {city}: {e}")

# ───────────────── background loop & Flask ────────────────────
def loop():
    n = 0
    while True:
        print(f"HB {n}"); n += 1
        scrape_once()
        time.sleep(60)

app = Flask(__name__)
@app.route("/")
def root(): return "✅ WOKO bot is running"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=False)
