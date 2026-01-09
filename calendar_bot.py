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
    """
    날짜 문자열 파싱 (예: 02.02(월) ~ 02.27(금))
    """
    # 괄호와 요일 제거
    clean_str = re.sub(r'\([가-힣]\)', '', date_str)
    
    if "~" in clean_str:
        start_str, end_str = clean_str.split("~")
    else:
        start_str = clean_str
        end_str = clean_str
        
    start_str = start_str.strip()
    end_str = end_str.strip()
    
    # 연도 붙여서 날짜 객체로 변환
    start_date = datetime.strptime(f"{current_year}.{start_str}", "%Y.%m.%d").date()
    end_date = datetime.strptime(f"{current_year}.{end_str}", "%Y.%m.%d").date()
    
    return start_date, end_date

def get_calendar_events():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
        response.encoding = 'utf-8' 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        events = []
        now = datetime.now()
        current_year = now.year 

        print(f"📡 페이지 접속 상태: {response.status_code}")
        
        # 1. 페이지 내의 모든 'li' 태그를 가져옵니다.
        all_list_items = soup.find_all("li")
        print(f"🔍 페이지 내 전체 목록(li) 개수: {len(all_list_items)}개")
        
        # 디버깅용: 봇이 보고 있는 텍스트가 뭔지 확인 (앞부분 5개만 출력)
        print("--- [디버깅] 봇이 읽은 목록 내용 예시 (상위 5개) ---")
        for i, item in enumerate(all_list_items[:5]):
            print(f"{i+1}. {item.get_text(strip=True)[:30]}...") 
        print("--------------------------------------------------")

        count = 0
        for item in all_list_items:
            # 2. 태그 상관없이 '텍스트'만 싹 긁어옵니다.
            full_text = item.get_text(" ", strip=True) # 공백을 띄어쓰기로 변환
            
            # 3. 정규식(Regex)으로 날짜 패턴을 찾습니다.
            # 패턴: 숫자2개.숫자2개(한글요일) ~ 숫자2개.숫자2개(한글요일)
            # 예: 02.02(월) ~ 02.27(금) 또는 02.20(금)
            match = re.search(r'(\d{2}\.\d{2}\([가-힣]\)(?:\s*~\s*\d{2}\.\d{2}\([가-힣]\))?)', full_text)
            
            if match:
                date_part = match.group(1) # 찾은 날짜 부분
                
                # 전체 텍스트에서 날짜 부분을 뺀 나머지를 '제목'으로 간주
                # 예: "02.20(금) 입학식" -> "입학식"
                title_part = full_text.replace(date_part, "").strip()
                
                # 제목이 너무 짧으면(1글자 이하) 스킵 (쓰레기 데이터 방지)
                if len(title_part) < 2:
                    continue

                try:
                    s_date, e_date = parse_date(date_part, current_year)
                    events.append({
                        "title": title_part,
                        "start": s_date,
                        "end": e_date
                    })
                    count += 1
                except Exception:
                    continue

        print(f"✅ 학사일정 패턴 일치 항목: {count}개 찾음")
        
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
        if event['start'] <= today <= event['end']:
            today_events.append(event['title'])
        
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
