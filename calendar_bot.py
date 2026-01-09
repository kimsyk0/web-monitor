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
    '02.20(금)' 또는 '02.02(월) ~ 02.27(금)' 형태를 파싱
    """
    # 괄호와 요일 제거 -> '02.20' 또는 '02.02 ~ 02.27'
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
        # 인코딩 강제 설정 (한글 깨짐 방지)
        response.encoding = 'utf-8' 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        events = []
        now = datetime.now()
        current_year = now.year 

        print(f"📡 웹페이지 접속 성공 (상태코드: {response.status_code})")

        # 1차 시도: 개발자 도구상의 정확한 경로 (schedule-list-box > list > ul > li)
        list_items = soup.select("div.schedule-list-box div.list ul li")
        
        # 2차 시도: 못 찾았다면 조금 더 넓게 찾기 (schedule-list-box > ... > li)
        if not list_items:
            print("⚠️ 1차 탐색 실패, 2차 시도 중...")
            list_items = soup.select("div.schedule-list-box li")
            
        # 3차 시도: 그래도 없다면 그냥 'list' 클래스 안의 li 찾기
        if not list_items:
            print("⚠️ 2차 탐색 실패, 3차 시도 중 (광범위 탐색)...")
            list_items = soup.select("div.list ul li")

        print(f"🔍 발견된 리스트 항목 수: {len(list_items)}개")

        for item in list_items:
            try:
                # strong 태그: 날짜 (예: 02.20(금))
                date_tag = item.select_one("strong")
                # p 태그: 행사명
                title_tag = item.select_one("p")
                
                # 태그가 없으면 텍스트에서라도 찾기 시도 (예외 처리)
                if not date_tag:
                    continue
                    
                date_text = date_tag.get_text(strip=True)
                # p 태그가 없으면 strong 태그 형제 텍스트나 span 등 다른거 찾기
                if title_tag:
                    title_text = title_tag.get_text(strip=True)
                else:
                    # p태그가 없다면 strong 태그를 제외한 나머지 텍스트 가져오기
                    title_text = item.get_text(strip=True).replace(date_text, "").strip()
                
                if not date_text or not title_text:
                    continue

                # 날짜 파싱
                s_date, e_date = parse_date(date_text, current_year)
                
                events.append({
                    "title": title_text,
                    "start": s_date,
                    "end": e_date
                })
            except Exception as e:
                # 특정 항목 파싱 실패 시 로그만 찍고 계속 진행
                # print(f"항목 파싱 에러: {e}")
                continue

        # 날짜순 정렬
        events.sort(key=lambda x: x['start'])
        return events

    except Exception as e:
        print(f"❌ 크롤링 치명적 오류: {e}")
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
    
    print(f"📅 오늘 날짜(시스템): {today}")
    
    events = get_calendar_events()
    
    if not events:
        print("❌ 일정을 가져오지 못했습니다. (목록이 비어있음)")
        return

    today_events = []
    upcoming_events = []
    
    for event in events:
        # 1. 오늘 일정
        if event['start'] <= today <= event['end']:
            today_events.append(event['title'])
        
        # 2. 다가오는 일정 (오늘 < 시작일)
        if event['start'] > today:
            d_day = (event['start'] - today).days
            if d_day <= 60:
                upcoming_events.append({
                    "title": event['title'],
                    "d_day": d_day,
                    "date": event['start'].strftime("%m/%d")
                })

    if not today_events and not upcoming_events:
        print("📭 전송할 알림이 없습니다. (조건에 맞는 일정이 없음)")
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
    print("✅ 메시지 생성 완료:")
    print(final_msg)
    
    send_telegram(final_msg)

if __name__ == "__main__":
    run()
