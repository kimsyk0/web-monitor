import os
import requests
from playwright.sync_api import sync_playwright

# ▼▼▼ 설정 ▼▼▼
TARGET_URL = "https://www.kw.ac.kr/ko/life/notice.jsp"
# 선택자를 조금 더 넓게 잡아서 오류 확률을 줄입니다.
SELECTOR = ".board-list-box .title-comm a" 
# ▲▲▲▲▲▲▲▲▲▲

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
        # 1. 브라우저를 띄울 때 "사람인 척" 하는 설정 추가
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1920, "height": 1080} # PC 화면 크기로 고정
        )
        page = context.new_page()
        
        try:
            print(f"접속 시도: {TARGET_URL}")
            page.goto(TARGET_URL)
            
            # 로딩 시간을 10초 -> 30초로 늘려줍니다
            page.wait_for_selector(SELECTOR, timeout=30000)
            
            # 가장 위에 있는 글(첫번째)만 가져옵니다
            element = page.locator(SELECTOR).first
            
            current_title = element.inner_text().strip()
            link_suffix = element.get_attribute("href")
            full_link = f"https://www.kw.ac.kr{link_suffix}" if link_suffix else TARGET_URL
            
            print(f"가져온 제목: {current_title}")

            # 파일 저장/비교 로직
            last_title = "NONE"
            if os.path.exists("data.txt"):
                with open("data.txt", "r", encoding="utf-8") as f:
                    last_title = f.read().strip()

            if last_title != current_title:
                print("✨ 새로운 공지 발견! 메시지 전송 중...")
                msg = f"📢 [광운대 공지]\n{current_title}\n\n{full_link}"
                send_telegram(msg)
                
                with open("data.txt", "w", encoding="utf-8") as f:
                    f.write(current_title)
            else:
                print("변경 사항 없음 (정상 작동)")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            # 오류가 나면 나한테 알려주도록 설정 (테스트용)
            send_telegram(f"봇 오류 발생: {e}")
            raise e # GitHub Actions에서 빨간 X가 뜨도록 강제로 에러 발생시킴
        
        finally:
            browser.close()

if __name__ == "__main__":
    run()
