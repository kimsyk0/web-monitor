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
    # 괄호와 요일 제거 및 공백 정리
    clean_str = re.sub(r'\([가-힣]\)', '', date_str).strip()
    
    if "~" in clean_str:
        start_str, end_str = clean_str.split("~")
    else:
        start_str = clean_str
        end_str = clean_str
        
    start_str = start_str.strip()
    end_str = end_str.strip()
    
    # 날짜 변환
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
        
        # 스크립트와 스타일 태그 제거 (순수 텍스트만 남기기 위해)
        for script in soup(["script", "style"]):
            script.decompose()

        # 웹페이지의 모든 텍스트를 줄 단위로 리스트화
        all_lines = soup.get_text(separator="\n", strip=True).splitlines()
        
        print(f"📡 페이지 접속 상태: {response.status_code}")
        print(f"🔍 전체 텍스트 라인 수: {len(all_lines)}줄")
        
        events = []
        now = datetime.now()
        current_year = now.year 

        found_count = 0
        
        for line in all_lines:
            line = line.strip()
            if not line: continue
            
            # 정규식: "숫자.숫자" 패턴이 포함된 줄을 찾음
            # 예: "02.02(월) ~ 02.27(금) 2026학년도 1학기 복학신청"
            match = re.search(r'(\d{2}\.\d{2})', line)
            
            if match:
                # 정확한 날짜 포맷이 있는지 2차 검증 (요일 포함)
                date_match = re.search(r'(\d{2}\.\d{2}\([가-힣]\)(?:\s*~\s*\d{2}\.\d{2}\([가-힣]\))?)', line)
                
                if date_match:
                    date_part = date_match.group(1)
                    # 날짜를 뺀 나머지를 제목으로
                    title_part = line.replace(date_part, "").strip()
                    
                    # 제목이 너무 짧으면 패스
                    if len(title_part) < 2: continue

                    try:
                        s_date, e_date = parse_date(date_part, current_year)
                        
                        # 중복 방지 (같은 내용이 여러 줄에 걸쳐 나올 수 있음)
                        is_duplicate = False
                        for e in events:
                            if e['title'] == title_part and e['start'] == s_date:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            events.append({
                                "title": title_part,
                                "start": s_date,
                                "end": e_date
                            })
                            found_count += 1
                    except Exception:
                        continue

        print(f"✅ 최종 추출된 학사일정: {found_count}개")
        
        # 디버깅: 만약 0개라면 봇이 본 텍스트 일부 출력
        if found_count == 0:
            print("--- [디버깅] 봇이 본 텍스트 상위 20줄 ---")
            for l in all_lines[:20]:
                print(l)
            print("------------------------------------------")

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
        print("❌ 일정을 가져오지 못했습니다. (텍스트 스캔 실패)")
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
