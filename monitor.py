import os
import requests
from bs4 import BeautifulSoup
import urllib3

# 보안 경고 무시 (학교 사이트 접속 시 필수)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ▼ 설정 ▼
TARGET_URL = "https://www.kw.ac.kr/ko/life/notice.jsp"
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.get(url, params={"chat_id": CHAT_ID, "text": msg})
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")

def run():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        print(f"접속 시도: {TARGET_URL}")
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 게시글 리스트 가져오기
        items = soup.select(".board-list-box ul li")
        
        if not items:
            print("❌ 오류: 게시글을 찾을 수 없습니다.")
            return

        # 2. 상위 5개 글 수집 (제목|링크)
        current_posts = []
        check_count = min(len(items), 5) # 상위 5개만 확인
        
        print(f"🔍 상위 {check_count}개 글 분석 중...")

        for i in range(check_count):
            item = items[i]
            # 제목과 링크 추출 (구조에 따라 a태그 위치가 다를 수 있어 두 가지 경우 다 체크)
            a_tag = item.select_one("div.board-text > a") or item.select_one("a")
            
            if a_tag:
                # 공백/줄바꿈 제거하여 깔끔하게 만듦
                title = " ".join(a_tag.get_text().split())
                link = a_tag.get('href')
                full_link = f"https://www.kw.ac.kr{link}" if link else TARGET_URL
                
                # 데이터 저장용 문자열 생성
                current_posts.append(f"{title}|{full_link}")
                print(f"  [{i+1}] {title[:20]}...")

        # 3. 이전 데이터 불러오기
        old_posts = []
        if os.path.exists("data.txt"):
            with open("data.txt", "r", encoding="utf-8") as f:
                old_posts = [line.strip() for line in f.readlines()]

        # 4. 비교 및 알림
        new_found_count = 0
        
        # 파일이 아예 없거나(첫 실행), 내용이 다르면 알림
        if old_posts:
            for post_data in current_posts:
                if post_data not in old_posts:
                    title, link = post_data.split("|")
                    print(f"✨ 새로운 글 발견: {title}")
                    
                    msg = f"📢 [광운대 새 공지]\n{title}\n\n{link}"
                    send_telegram(msg)
                    new_found_count += 1
        else:
            # data.txt가 비어있거나 처음일 때는 알림을 보내지 않고 데이터만 채움 (폭탄 방지)
            print("첫 실행이거나 초기화됨. 현재 데이터를 기준으로 잡습니다.")

        if new_found_count == 0:
            print("변경 사항 없음")

        # 5. 현재 상태 저장
        with open("data.txt", "w", encoding="utf-8") as f:
            for post in current_posts:
                f.write(post + "\n")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        # 오류 발생 시에도 알림을 받고 싶으면 아래 주석 해제
        # send_telegram(f"봇 오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    run()
