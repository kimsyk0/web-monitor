import os
import requests
from playwright.sync_api import sync_playwright

# ▼▼▼ 여기만 수정하면 됩니다 ▼▼▼
TARGET_URL = "https://www.kw.ac.kr/ko/life/notice.jsp"  # 감시할 사이트 주소
SELECTOR = ".board-list-box tbody tr:nth-child(1) .title-comm a"            # 감시할 요소 (구글 로고)
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
        except:
            pass

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(TARGET_URL)
            page.wait_for_selector(SELECTOR, timeout=10000)
            
            # 요소의 텍스트가 없으면(이미지 등) 속성값이라도 가져옴
            element = page.locator(SELECTOR)
            current_data = element.inner_text().strip()
            if not current_data: 
                # 텍스트가 없으면 alt 태그나 src 등을 가져와서 비교
                current_data = element.get_attribute("alt") or "이미지/요소 있음"

            print(f"현재 데이터: {current_data}")

            try:
                with open("data.txt", "r", encoding="utf-8") as f:
                    last_data = f.read().strip()
            except FileNotFoundError:
                last_data = "NONE"

            if last_data != current_data:
                msg = f"🔔 [변경 감지!]\n사이트: {TARGET_URL}\n\n내용이 변경되었습니다."
                print(msg)
                send_telegram(msg)
                
                with open("data.txt", "w", encoding="utf-8") as f:
                    f.write(current_data)
            else:
                print("변경 사항 없음")

        except Exception as e:
            print(f"에러: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
