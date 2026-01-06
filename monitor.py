import os
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URL = "https://www.kw.ac.kr/ko/life/notice.jsp"
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        print("❌ 오류: 텔레그램 설정(Secrets)이 비어있습니다!")
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        # 실제 전송 결과(res)를 받아서 확인합니다.
        res = requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
        
        # 성공(200)이 아니면 에러 내용을 출력
        if res.status_code == 200:
            print("✅ 텔레그램 전송 성공")
        else:
            print(f"❌ 텔레그램 전송 실패! (코드: {res.status_code})")
            print(f"👉 이유: {res.text}") # 여기가 핵심!
            
    except Exception as e:
        print(f"텔레그램 접속 에러: {e}")

def run():
    # ... (아래는 기존 코드와 동일, 생략 가능하지만 편의를 위해 전체 제공) ...
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select(".board-list-box ul li")

        if not items:
            print("❌ 오류: 게시글 못 찾음")
            return

        # 테스트를 위해 무조건 1개 보내보기
        print("🔔 테스트 메시지 전송 시도 중...")
        send_telegram("테스트 메시지입니다. 이게 보이면 성공!")

        # (기존 로직은 잠시 생략하거나 그대로 둬도 됨)

    except Exception as e:
        print(f"오류: {e}")
        exit(1)

if __name__ == "__main__":
    run()
