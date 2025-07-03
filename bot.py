import os, time, requests
from flask import Flask
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from telegram import Bot

# Telegram
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")           # keep the SAME key name everywhere
tg      = Bot(TOKEN)

# Flask (keeps Render happy)
app = Flask(__name__)
@app.route('/')
def root(): return "✅ WOKO bot is alive"

# Selenium helper
def make_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

URLS = {
    "Zürich"                 : "https://www.woko.ch/de/zimmer-in-zuerich",
    "Winterthur + Wädenswil" : "https://www.woko.ch/de/zimmer-in-winterthur-und-waedenswil",
    "Wädenswil"              : "https://www.woko.ch/de/zimmer-in-waedenswil"
}

def scrape():
    drv = make_driver()
    for city, url in URLS.items():
        print(f"🔎  {city}")
        try:
            drv.get(url)
            time.sleep(4)                       # allow JS to finish
            soup = BeautifulSoup(drv.page_source, "html.parser")

            # WOKO pages put each advert into div.offer OR div.grid-item
            box = soup.select_one("div.offer, div.grid-item")
            if not box:
                tg.send_message(CHAT_ID, f"⚠️ No listings found on WOKO for {city}.")
                continue

            title = (box.find("h3") or box.find("h2")).get_text(strip=True)
            link_tag = box.find("a" , href=True)
            link = "https://www.woko.ch" + link_tag["href"] if link_tag else url

            msg = f"🏠 <b>{title}</b>\n🔗 {link}\n📍 {city}"
            tg.send_message(CHAT_ID, msg, parse_mode="HTML")
        except Exception as e:
            tg.send_message(CHAT_ID, f"❌ Error checking {city}: {e}")
            print("ERROR:", e)

    drv.quit()

if __name__ == "__main__":
    print("🤖 Bot running …")
    scrape()                 # first run immediately
    app.run(host="0.0.0.0", port=8080)   # keep container alive
