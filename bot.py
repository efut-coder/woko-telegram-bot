import os, time, threading, requests
from flask import Flask
from bs4 import BeautifulSoup

TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"
def tg(txt): requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": txt, "parse_mode": "HTML"}, timeout=8)

PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}
sent=set()

UA = {
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "de,en;q=0.9"
}

def scrape_once():
    print("DEBUG: entered scrape_once()")          # <── must appear
    for city,url in PAGES.items():
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()

            soup  = BeautifulSoup(r.text, "html.parser")
            boxes = soup.select("div.row.offer") or soup.select("div.grid-item")

            print(f"▶ {city}: {len(boxes)} boxes")

            if not boxes:
                tg(f"⚠️ No listings on {city}")
                continue

            first   = boxes[0]
            a_tag   = first.find("a", href=True)
            title   = (first.find(['h3','h2']) or a_tag).get_text(strip=True)
            link    = "https://www.woko.ch"+a_tag["href"] if a_tag else url

            if link in sent: continue
            sent.add(link)
            tg(f"🏠 <b>{title}</b>\n🔗 {link}\n📍 {city}")

        except Exception as e:
            print("ERR:", city, e)
            tg(f"❌ {city}: {e}")

def loop():
    i=0
    while True:
        print("HB", i); i+=1
        try:
            scrape_once()
        except Exception as e:                       # catch everything
            print("FATAL in scrape_once:", e)
            tg(f"💥 Fatal error: {e}")
        time.sleep(60)

app = Flask(__name__)
@app.route("/")
def root(): return "✅ running"

if __name__=="__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",8080)), threaded=False)
