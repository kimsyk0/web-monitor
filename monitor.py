import os
import requests
from bs4 import BeautifulSoup
import urllib3

# 보안 경고 무시
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
        
        # 1. 게시글 리스트 가져오기 (고정 공지 포함, 전부 다)
        items = soup.select(".board-list-box ul li")
        
        if not items:
            print("❌ 오류: 게시글을 찾을 수 없습니다.")
            return

        # 2. 상위 5개 글의 제목을 수집 (New 아이콘 여부도 확인 가능하지만 제목으로 충분)
        current_posts = []
        check_count = min(len(items), 5) # 최대 5개까지만 확인
        
        print(f"🔍 상위 {check_count}개 글 분석 중...")

        for i in range(check_count):
            item = items[i]
            # 제목과 링크 추출
            a_tag = item.select_one("div.board-text > a") or item.select_one("a")
            if a_tag:
                title = " ".join(a_tag.get_text().split()) # 공백 제거
                link = a_tag.get('href')
                full_link = f"https://www.kw.ac.kr{link}" if link else TARGET_URL
                
                # 데이터 저장용 리스트에 추가 (제목|링크)
                current_posts.append(f"{title}|{full_link}")
                print(f"  [{i+1}] {title[:30]}...")

        # 3. 이전 데이터 불러오기
        old_posts = []
        if os.path.exists("data.txt"):
            with open("data.txt", "r", encoding="utf-8") as f:
                # 파일에는 제목|링크 형태로 줄바꿈되어 저장됨
                old_posts = [line.strip() for line in f.readlines()]

        # 4. 비교 로직 (새로운 글 찾기)
        # "지금 가져온 5개 중에, 옛날 파일에는 없던 게 있는가?"
        new_found_count = 0
        
        # 첫 실행이 아닐 때만 알림 (old_posts가 비어있으면 첫 실행)
        if old_posts:
            for post_data in current_posts:
                # 저장된 리스트에 이 제목|링크가 없다면? -> 신규 게시글!
                if post_data not in old_posts:
                    title, link = post_data.split("|")
                    print(f"✨ 새로운 글 발견: {title}")
                    
                    msg = f"📢 [광운대 새 공지]\n{title}\n\n{link}"
                    send_telegram(msg)
                    new_found_count += 1
        
        if new_found_count == 0:
            print("변경 사항 없음")
        else:
            print(f"총 {new_found_count}개의 새 글 알림 전송 완료")

        # 5. 현재 데이터를 파일에 저장 (덮어쓰기)
        with open("data.txt", "w", encoding="utf-8") as f:
            for post in current_posts:
                f.write(post + "\n")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    run()
