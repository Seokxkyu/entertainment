import os
import time
import glob
import re
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager 

# ───────────────────────────────────────────────────
# 1) 환경 설정
# ───────────────────────────────────────────────────
DOWNLOAD_FOLDER   = os.path.join(os.getcwd(), "data", "ytweekly")
CSV_PATH          = os.path.join(os.getcwd(), "data", "us_weekly_yt.csv")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ───────────────────────────────────────────────────
# 2) Selenium 초기화
# ───────────────────────────────────────────────────
def init_driver():
    opts = Options()
    opts.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    opts.add_argument("--headless")   
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-US")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # ChromeDriverManager로 자동 설치된 드라이버 사용
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

# ───────────────────────────────────────────────────
# 3) 마지막 목요일 이후 날짜 계산
# ───────────────────────────────────────────────────
def get_next_thursdays(csv_path: str) -> list[str]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"{csv_path} 이 없습니다.")
    df = pd.read_csv(csv_path, dtype={'date': str})
    df['date'] = pd.to_datetime(df['date'], format="%Y%m%d")
    last_thu = df['date'].max()
    dates = []
    current = last_thu + timedelta(days=7)
    today   = datetime.today()
    while current < today:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=7)
    return dates

# ───────────────────────────────────────────────────
# 4) 차트 페이지 접속 → CSV 다운로드
# ───────────────────────────────────────────────────
def download_chart_for_date(driver, date_str: str):
    wait = WebDriverWait(driver, 10)
    url  = f"https://charts.youtube.com/charts/TopArtists/us/weekly/{date_str}"
    print(f"\n▶ 접속: {url}")
    driver.get(url)
    try:
        btn = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "/html/body/ytmc-v2-app/ytmc-detailed-page/div[1]/ytmc-top-banner/"
            "div[2]/div[4]/paper-icon-button[2]"
        )))
    except:
        btn = wait.until(EC.element_to_be_clickable((By.ID, "download-button")))
    btn.click()
    print(f"✅ [{date_str}] 다운로드 클릭")
    time.sleep(3)

# ───────────────────────────────────────────────────
# 5) CSV 파싱 보조: artist에 쉼표가 있어도 안전
# ───────────────────────────────────────────────────
def parse_line(line: str) -> list[str]:
    parts = line.rstrip("\n").split(",")
    if len(parts) == 6:
        return parts
    rank, prev = parts[0], parts[1]
    growth     = parts[-1]
    views      = parts[-2]
    periods    = parts[-3]
    artist     = ",".join(parts[2:-3])
    return [rank, prev, artist, periods, views, growth]

# ───────────────────────────────────────────────────
# 6) 새로 받은 파일들을 통합본에 append
# ───────────────────────────────────────────────────
def append_new_data(csv_path: str, download_folder: str, dates: list[str]):
    df_existing = pd.read_csv(csv_path, dtype={'date': str})

    merged = []
    for d in dates:
        pattern = os.path.join(download_folder, f"youtube-charts-top-artists-us-weekly-{d}.csv")
        if not os.path.exists(pattern):
            print(f"⚠️ {os.path.basename(pattern)} 없음, 건너뜀")
            continue

        with open(pattern, encoding="utf-8") as f:
            lines = [ln for ln in f.readlines() if ln.strip()]

        header = lines[0].strip().split(",")  
        rows   = [parse_line(ln) for ln in lines[1:]]

        df_new = pd.DataFrame(rows, columns=header)
        df_new.insert(0, "date", d)  
        merged.append(df_new)

    if not merged:
        print("🚫 추가할 데이터가 없습니다.")
        return

    df_all = pd.concat([df_existing] + merged, ignore_index=True)
    df_all.drop_duplicates(subset=["date", "Rank", "Artist Name"], inplace=True)
    df_all.to_csv(csv_path, index=False, encoding="utf-8-sig")
    total_new = sum(len(df) for df in merged)
    print(f"📝 {total_new}개 레코드 추가 후 저장: {csv_path}")

# ───────────────────────────────────────────────────
# 7) 메인 실행
# ───────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        dates = get_next_thursdays(CSV_PATH)
        if not dates:
            print("✅ 최신까지 수집 완료.")
        else:
            print(f"📅 수집할 주차: {dates}")
            drv = init_driver()
            for dt in dates:
                download_chart_for_date(drv, dt)
            drv.quit()
            print("\n✅ 다운로드 완료, 브라우저 종료.")
            append_new_data(CSV_PATH, DOWNLOAD_FOLDER, dates)

    except Exception as e:
        print(f"❌ 오류: {e}")