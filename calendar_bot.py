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
    """
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
    except Exception as e:
        print(f"   [!] 날짜 파싱 실패: {date_str} -> {e}")
        return None, None

def run():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ▼ 디버깅 1: 선택자로 찾은 요소 개수 확인 ▼
        # 기존 선택자: "div.schedule-list-box.schedule-this-yearlist ul li"
        # 혹시 구조가 다를 수 있으니 조금 더 넓은 범위로 찾아서 로그를 찍습니다.
        items = soup.select("div.schedule-list-box.schedule-this-yearlist ul li")
        
        print(f"🔍 DEBUG: 찾은 리스트 항목 수: {len(items)}개")
        
        if len(items) == 0:
            print("❌ 오류: 리스트를 찾지 못했습니다. HTML 구조가 변경되었거나 로딩되지 않았습니다.")
            # HTML 일부를 찍어서 확인 (너무 길 수 있으니 앞부분만)
            print(f"Dump HTML(500자): {soup.prettify()[:500]}")
        
        today = date.today()
        # today = date(2026, 2, 20) # 테스트용 고정 날짜
        
        today_events = []
        upcoming_events = []

        print(f"기준 날짜: {today}")

        for i, item in enumerate(items):
            date_tag = item.select_one("strong")
            title_tag = item.select_one("p")

            # ▼ 디버깅 2: 읽은 내용 그대로 출력 ▼
            raw_date_text = date_tag.get_text(strip=True) if date_tag else "날짜없음"
            raw_title_text = title_tag.get_text(strip=True) if title_tag else "제목없음"
            print(f"[{i}] 읽음: {raw_date_text} | {raw_title_text}")

            if not date_tag or not title_tag:
                continue

            # 날짜 파싱
            start_date, end_date = parse_date_range(raw_date_text, today.year)
            
            if not start_date:
                continue

            # 1. 오늘의 일정 (기간 포함)
            if start_date <= today <= end_date:
                today_events.append(f"• {raw_title_text}")

            # 2. 다가오는 일정 (오늘 이후 시작)
            elif start_date > today:
                d_day = (start_date - today).days
                upcoming_events.append({
                    "date": raw_date_text,
                    "title": raw_title_text,
                    "d_day": d_day,
                    "sort_date": start_date
                })

        # 정렬 및 상위 2개 추출
        upcoming_events.sort(key=lambda x: x["sort_date"])
        next_two = upcoming_events[:2]

        # ▼ 메시지 구성 (구분선 제거됨) ▼
        msg_lines = []
        msg_lines.append(f"📅 *오늘의 학사일정* ({today.strftime('%Y-%m-%d')})\n")
        
        if today_events:
            msg_lines.append("\n".join(today_events))
        else:
            msg_lines.append("• 오늘 예정된 학사일정이 없습니다.")
        
        msg_lines.append("\n🔜 *다가오는 일정*")
        
        if next_two:
            for event in next_two:
                msg_lines.append(f"\n[{event['date']}] (D-{event['d_day']})\n👉 {event['title']}")
        else:
             msg_lines.append("\n(예정된 일정이 없습니다)")

        msg_lines.append(f"\n[🔗 전체 일정 보기]({TARGET_URL})")

        final_msg = "\n".join(msg_lines)
        print("--- 전송할 메시지 미리보기 ---")
        print(final_msg)
        
        send_telegram(final_msg)

    except Exception as e:
        print(f"❌ 치명적 오류 발생: {e}")
        exit(1)

if __name__ == "__main__":
    run()
