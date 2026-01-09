import os
import time
from datetime import datetime
import re
import pytz
from bs4 import BeautifulSoup
import requests

# ▼ 셀레니움 라이브러리 ▼
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ▼ 설정 ▼
TARGET_URL = "https://www.kw.ac.kr/ko/life/bachelor_calendar.jsp"
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def parse_date(date_str, current_year):
    # 1. 괄호 및 요일 제거 (02.02(월) -> 02.02)
    clean_str = re.sub(r'\([가-힣]\)', '', date_str).strip()
    
    # 2. 물결표(~), 줄표(-) 등 다양한 구분자 처리
    if "~" in clean_str:
        parts = clean_str.split("~")
    elif "-" in clean_str:
        parts = clean_str.split("-")
    else:
        parts = [clean_str, clean_str]
        
    if len(parts) >= 2:
        start_str = parts[0].strip()
        end_str = parts[1].strip()
    else:
        start_str = parts[0].strip()
        end_str = parts[0].strip()
    
    try:
        start_date = datetime.strptime(f"{current_year}.{start_str}", "%Y.%m.%d").date()
        end_date = datetime.strptime(f"{current_year}.{end_str}", "%Y.%m.%d").date()
        return start_date, end_date
    except ValueError:
        return None, None

def get_calendar_with_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    print("🚀 크롬 브라우저 실행 중...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        print(f"📡 접속 중: {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # 1. 로딩 대기 (schedule-this-yearlist 안의 li가 생길 때까지)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".schedule-this-yearlist li"))
            )
            print("✨ 데이터 로딩 감지됨!")
        except:
            print("⚠️ 대기 시간 초과, 스크롤 후 텍스트 스캔 시도")

        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()

        # 텍스트 라인 추출 (공백 제거 후 리스트화)
        all_lines = [line.strip() for line in soup.get_text(separator="\n", strip=True).splitlines() if line.strip()]
        print(f"🔍 읽어온 유효 텍스트 라인 수: {len(all_lines)}줄")
        
        events = []
        now = datetime.now()
        current_year = now.year 
        found_count = 0
        
        # ▼▼▼ [최종 수정] 유연한 파싱 로직 ▼▼▼
        i = 0
        while i < len(all_lines):
            line = all_lines[i]
            
            # 날짜 패턴 찾기 (공백 포함 허용, 줄 중간에 있어도 찾음)
            # 예: "02.02" 또는 "02.02(월)"
            date_match = re.search(r'(\d{2}\.\d{2})', line)
            
            if date_match:
                # 더 정확한 날짜 구간 패턴 확인 (요일 포함)
                # 예: 02.02(월) ~ 02.27(금)
                full_date_match = re.search(r'(\d{2}\.\d{2}\([가-힣]\)(?:\s*[~-]\s*\d{2}\.\d{2}\([가-힣]\))?)', line)
                
                if full_date_match:
                    date_part = full_date_match.group(0) # 매칭된 날짜 문자열 전체
                    
                    # 1. 같은 줄에 제목이 있는지 확인
                    # 날짜 부분을 지웠을 때 남는 글자가 있으면 그게 제목!
                    title_part = line.replace(date_part, "").strip()
                    
                    # 2. 같은 줄에 제목이 없다면(너무 짧다면), 다음 줄을 제목으로 가져옴
                    if len(title_part) < 2 and (i + 1 < len(all_lines)):
                        next_line = all_lines[i+1]
                        # 다음 줄이 또 날짜가 아니라면 제목으로 인정
                        if not re.search(r'\d{2}\.\d{2}', next_line):
                            title_part = next_line
                            i += 1 # 다음 줄은 제목으로 썼으니 건너뜀
                    
                    # 제목이 여전히 없거나 날짜라면 스킵
                    if len(title_part) < 2 or re.search(r'\d{2}\.\d{2}', title_part):
                        i += 1
                        continue

                    try:
                        s_date, e_date = parse_date(date_part, current_year)
                        
                        if s_date and e_date:
                            # 중복 방지
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
                    except Exception as e:
                        print(f"파싱 에러({line}): {e}")
            
            i += 1
            
        print(f"✅ 최종 추출된 일정: {found_count}개")
        events.sort(key=lambda x: x['start'])
        return events

    except Exception as e:
        print(f"❌ 브라우저 에러: {e}")
        return []
    finally:
        driver.quit()

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
    
    events = get_calendar_with_selenium()
    
    if not events:
        print("❌ 일정을 가져오지 못했습니다.")
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
        print("📭 전송할 내용이 없습니다.")
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
