import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send_telegram_message(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    )

def check_woko():
    print("🔁 tick: открываю страницу и проверяю объявления…")
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get("https://www.woko.ch")
        time.sleep(3)
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(),'Accept all')]")
            btn.click()
            print("🍪 cookies приняты")
            time.sleep(1)
        except Exception:
            print("🍪 popup с cookies не найден")

        html = driver.page_source
        print("=== page source начало ===")
        print(html[:5000])
        print("=== page source конец ===")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Выводим все подходящие блоки для отладки
        boxes = soup.select("div.grid-item")
        print(f"Найдено блоков div.grid-item: {len(boxes)}")
        for i, box in enumerate(boxes[:5]):
            print(f"Блок {i}:\n", box.prettify()[:500])

        # Пробуем найти первое валидное объявление
        for box in boxes:
            title = box.find("h3")
            date = box.find(lambda tag: tag.name == "p" and tag.get_text(strip=True)[0].isdigit())
            addr = box.find("div", class_="address")
            price = box.find("div", class_="price")
            if title and date and addr:
                msg = f"<b>{title.get_text(strip=True)}</b>\n🗓 {date.get_text(strip=True)}\n🏠 {addr.get_text(strip=True)}"
                if price:
                    msg += f"\n💰 {price.get_text(strip=True)}"
                print("➡️ отправляю в Telegram:", msg)
                send_telegram_message(msg)
                break
        else:
            send_telegram_message("⚠️ No listings found on WOKO")
            print("‼️ Нет ни одного валидного объявления")

    except Exception as e:
        send_telegram_message(f"❌ ERROR: {e}")
        print("Ошибка:", e)
    finally:
        driver.quit()

if __name__ == "__main__":
    # для быстрой проверки один раз
    check_woko()
