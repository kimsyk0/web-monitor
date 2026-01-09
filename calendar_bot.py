import os
import requests
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime, date

# SSL 인증서 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ▼ 설정 ▼
TARGET_URL = "https://www.kw.ac.kr/ko/life/bachelor_calendar.jsp"
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(url, data=payload)
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")

def parse_date_range(date_str, current_year):
    """
    날짜 문자열을 파싱하여 시작일(date)과 종료일(date)을 반환합니다.
    예: "02.02(월)" -> (2026-02-02, 2026-02-02)
    예: "02.02(월) ~ 02.27(금)" -> (2026-02-02, 2026-02-27)
    """
    # 괄호와 요일 제거 (예: "02.02" 또는 "02.02 ~ 02.27")
    clean_str = date_str
    for char in "월화수목금토일() ":
        clean_str = clean_str.replace(char, "")
    
    parts = clean_str.split("~")
    
    try:
        start_md = parts[0].strip().split(".")
        start_date = date(current_year, int(start_md[0]), int(start_md[1]))
        
        if len(parts) > 1:
            end_md = parts[1].strip().split(".")
            end_date = date(current_year, int(end_md[0]), int(end_md[1]))
        else:
            end_date = start_date
            
        return start_date, end_date
    except:
        return None, None

def run():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 스크린샷에 기반한 선택자: 전체 년도 리스트 안의 모든 li
        items = soup.select("div.schedule-list-box.schedule-this-yearlist ul li")
        
        today = date.today()
        # today = date(2026, 2, 20) # 테스트용 날짜 고정
        
        today_events = []
        upcoming_events = []

        print(f"기준 날짜: {today}")

        for item in items:
            date_tag = item.select_one("strong")
            title_tag = item.select_one("p")

            if not date_tag or not title_tag:
                continue

            raw_date = date_tag.get_text(strip=True)
            title = title_tag.get_text(strip=True)
            
            # 날짜 파싱 (올해 기준)
            start_date, end_date = parse_date_range(raw_date, today.year)
            
            if not start_date:
                continue

            # 1. 오늘의 일정인지 확인 (기간 내 포함 여부)
            if start_date <= today <= end_date:
                today_events.append(f"• {title}")

            # 2. 다가오는 일정인지 확인 (오늘 이후 시작하는 일정)
            elif start_date > today:
                # D-Day 계산
                d_day = (start_date - today).days
                upcoming_events.append({
                    "date": raw_date,
                    "title": title,
                    "d_day": d_day,
                    "sort_date": start_date
                })

        # 다가오는 일정 정렬 (날짜순) 및 상위 2개 추출
        upcoming_events.sort(key=lambda x: x["sort_date"])
        next_two = upcoming_events[:2]

        # ▼ 메시지 구성 ▼
        msg_lines = []
        msg_lines.append(f"📅 *오늘의 학사일정* ({today.strftime('%Y-%m-%d')})\n")
        
        # 오늘 일정 섹션
        if today_events:
            msg_lines.append("\n".join(today_events))
        else:
            msg_lines.append("• 오늘 예정된 학사일정이 없습니다.")
        
        msg_lines.append("\n━━━━━━━━━━━━━━━━━━")
        msg_lines.append("🔜 *다가오는 일정*")
        
        # 다가오는 일정 섹션
        if next_two:
            for event in next_two:
                msg_lines.append(f"\n[{event['date']}] (D-{event['d_day']})\n👉 {event['title']}")
        else:
             msg_lines.append("\n(예정된 일정이 없습니다)")

        msg_lines.append(f"\n[🔗 전체 일정 보기]({TARGET_URL})")

        final_msg = "\n".join(msg_lines)
        print(final_msg) # 로그 확인용
        send_telegram(final_msg)

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    run()
