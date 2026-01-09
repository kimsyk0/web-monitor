import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import pytz
import urllib3

# SSL 인증서 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ▼ 설정 ▼
TARGET_URL = "https://www.kw.ac.kr/ko/life/bachelor_calendar.jsp"
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def parse_date(date_str, current_year):
    # 괄호와 요일 제거
    clean_str = re.sub(r'\([가-힣]\)', '', date_str)
    
    if "~" in clean_str:
        start_str, end_str = clean_str.split("~")
    else:
        start_str = clean_str
        end_str = clean_str
        
    start_str = start_str.strip()
    end_str = end_str.strip()
    
    start_date = datetime.strptime(f"{current_year}.{start_str}", "%Y.%m.%d").date()
    end_date = datetime.strptime(f"{current_year}.{end_str}", "%Y.%m.%d").date()
    
    return start_date, end_date

def get_calendar_events():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
        response.encoding = 'utf-8' # 한글 깨짐 방지
        soup = BeautifulSoup(response.text, 'html.parser')
        
        events = []
        now = datetime.now()
        current_year = now.year 

        print(f"📡 페이지 접속 상태: {response.status_code}")
        
        # ▼ [수정 핵심] 특정 div 이름을 찾지 않고, 페이지 내의 모든 'li' 태그를 가져옵니다.
        all_list_items = soup.find_all("li")
        print(f"🔍 페이지 내 전체 목록(li) 개수: {len(all_list_items)}개")
        
        count = 0
        for item in all_list_items:
            # 1. li 태그 안에 strong(날짜) 태그가 있는지 확인
            date_tag = item.select_one("strong")
            # 2. li 태그 안에 p(제목) 태그가 있는지 확인
            title_tag = item.select_one("p")
            
            # 둘 중 하나라도 없으면 우리가 찾는 학사일정이 아님 -> 패스
            if not date_tag or not title_tag:
                continue
            
            date_text = date_tag.get_text(strip=True)
            title_text = title_tag.get_text(strip=True)
            
            # 날짜 형식이 '00.00' 형태인지 간단히 체크 (엉뚱한 strong 태그 방지)
            if not re.search(r'\d{2}\.\d{2}', date_text):
                continue
                
            try:
                s_date, e_date = parse_date(date_text, current_year)
                events.append({
                    "title": title_text,
                    "start": s_date,
                    "end": e_date
                })
                count += 1
            except Exception:
                continue

        print(f"✅ 학사일정 패턴 일치 항목: {count}개 찾음")
        
        # 날짜순 정렬
        events.sort(key=lambda x: x['start'])
        return events

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []

def send_telegram(msg):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=payload)

def run():
    kst = pytz.timezone('Asia/Seoul')
    today = datetime.now(kst).date()
    
    print(f"📅 기준 날짜: {today}")
    
    events = get_calendar_events()
    
    if not events:
        print("❌ 일정을 하나도 찾지 못했습니다.")
        return

    today_events = []
    upcoming_events = []
    
    for event in events:
        # 오늘 일정
        if event['start'] <= today <= event['end']:
            today_events.append(event['title'])
        
        # 다가오는 일정 (오늘 이후)
        if event['start'] > today:
            d_day = (event['start'] - today).days
            if d_day <= 60:
                upcoming_events.append({
                    "title": event['title'],
                    "d_day": d_day,
                    "date": event['start'].strftime("%m/%d")
                })

    if not today_events and not upcoming_events:
        print("📭 전송할 내용이 없습니다 (날짜 조건 불일치).")
        return

    msg_lines = []
    msg_lines.append(f"📆 *광운대 학사일정* ({today.strftime('%m/%d')})")
    
    if today_events:
        msg_lines.append("\n🔔 *오늘의 일정*")
        for title in today_events:
            msg_lines.append(f"• {title}")
    
    if upcoming_events:
        msg_lines.append("\n⏳ *다가오는 일정*")
        for item in upcoming_events[:2]: 
            msg_lines.append(f"• D-{item['d_day']} {item['title']} ({item['date']})")

    final_msg = "\n".join(msg_lines)
    print("메시지 미리보기:")
    print(final_msg)
    
    send_telegram(final_msg)

if __name__ == "__main__":
    run()
