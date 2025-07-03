import os, time, threading, requests
from bs4 import BeautifulSoup
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ─── Telegram ──────────────────────────────────────────────────────────────
TOKEN   = "7373000536:AAFCC_aocZE_mOegofnj63DyMtjQxkYvaN8"
CHAT_ID = "194010292"
def send(text: str):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
                  timeout=8)

# ─── Pages ─────────────────────────────────────────────────────────────────
PAGES = {
    "Zürich"                : "https://www.woko.ch/en/zimmer-in-zuerich",
    "Winterthur + Wädenswil": "https://www.woko.ch/en/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"             : "https://www.woko.ch/en/zimmer-in-waedenswil",
}

sent: set[str] = set()

# ─── Selenium helper ───────────────────────────────────────────────────────
def new_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(ChromeDriverManager().install(), options=opts)

def scrape_once():
    driver = new_driver()
    try:
        for city, url in PAGES.items():
            print(f"· {city}: loading page")
            driver.get(url)

            # click the “Free rooms” button if it exists
            try:
                btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                                    " 'abcdefghijklmnopqrstuvwxyz'), 'free rooms')]"))
                )
                btn.click()
                print(f"  clicked Free rooms for {city}")
            except Exception:
                print(f"  no Free rooms button on {city}")

            # wait until at least one listing box is in the DOM
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.row.offer"))
                )
            except Exception:
                send(f"⚠️ Kein Inserat gefunden ({city})")  # still nothing
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            first = soup.select_one("div.row.offer")
            if not first:
                send(f"⚠️ Kein Inserat gefunden ({city})")
                continue

            a  = first.find("a", href=True)
            h3 = first.find("h3")

            link  = "https://www.woko.ch" + a["href"] if a and a["href"].startswith("/") else (a["href"] if a else url)
            title = h3.get_text(" ", strip=True) if h3 else "No title"

            if link in sent:
                print(f"  already sent {link}")
                continue

            sent.add(link)
            send(f"🏠 <b>{title}</b>\n🔗 {link}\n📍 {city}")
            print(f"  sent: {title}")

    finally:
        driver.quit()

# ─── Loop + Flask keep-alive (Render) ──────────────────────────────────────
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
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=False)
