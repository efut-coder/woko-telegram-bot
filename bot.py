import os, time, threading, requests
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# ── Telegram (hard-coded) ─────────────────────────────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"
def tg(msg: str):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
                  timeout=8)

# ── Selenium headless Chrome factory ──────────────────────────
def driver():
    opt = Options()
    opt.add_argument("--headless")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opt)

PAGES = {
    "Zürich"                : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/de/zimmer-in-waedenswil",
}

sent: set[str] = set()

def scrape_once():
    drv = driver()
    for city, url in PAGES.items():
        print(f"▶ {city}")
        try:
            drv.get(url)

            # accept cookie banner if present
            try:
                WebDriverWait(drv, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'akzeptieren') or contains(.,'Accept all')]"))
                ).click()
            except Exception:
                pass

            # wait for at least one row.offer div (max 15 s)
            WebDriverWait(drv, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.row.offer"))
            )
        except Exception as e:
            print("ERR:", e)
            tg(f"❌ {city}: {e}")
            continue

        soup  = BeautifulSoup(drv.page_source, "html.parser")
        boxes = soup.select("div.row.offer")
        print(f"FOUND {len(boxes)} rows on {city}")

        if not boxes:
            tg(f"⚠️ no listings on {city}")
            continue

        first   = boxes[0]
        a_tag   = first.find("a", href=True)
        title   = (first.find(["h3","h2"]) or a_tag).get_text(strip=True)
        fullurl = "https://www.woko.ch" + a_tag["href"] if a_tag else url

        if fullurl in sent:
            continue
        sent.add(fullurl)
        tg(f"🏠 <b>{title}</b>\n🔗 {fullurl}\n📍 {city}")

    drv.quit()

def loop():
    i = 0
    while True:
        print(f"HB: minute {i}")
        scrape_once()
        i += 1
        time.sleep(60)

# ── Flask keep-alive for Render ───────────────────────────────
app = Flask(__name__)
@app.route("/")
def root(): return "✅ WOKO bot is running"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    port = int(os.getenv("PORT", 8080))
    print(f"Flask binding to port {port}")
    app.run(host="0.0.0.0", port=port, threaded=False)
