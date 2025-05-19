import os
import time
import glob
import re
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ───────────────────────────────────────────────────
# 1) 경로 설정
# ───────────────────────────────────────────────────
CHROMEDRIVER_PATH = r"C:\Users\rootn\OneDrive\Desktop\intern\chromedriver-win32\chromedriver-win32\chromedriver.exe"
DOWNLOAD_FOLDER   = os.path.join(os.getcwd(), "data", "spotdaily")
CSV_PATH          = os.path.join(os.getcwd(), "data", "us_daily_stream.csv")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ───────────────────────────────────────────────────
# 2) WebDriver 초기화
# ───────────────────────────────────────────────────
def init_driver():
    opts = Options()
    opts.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)

# ───────────────────────────────────────────────────
# 3a) 간단 로그인 시도
# ───────────────────────────────────────────────────
def try_simple_login(driver, user, pwd):
    wait = WebDriverWait(driver, 10)
    driver.get("https://accounts.spotify.com/ko/login?continue=https%3A%2F%2Fcharts.spotify.com/login")
    try:
        user_in = wait.until(EC.presence_of_element_located((By.ID, "login-username")))
        user_in.clear(); user_in.send_keys(user)
        pwd_in  = wait.until(EC.presence_of_element_located((By.ID, "login-password")))
        pwd_in.clear(); pwd_in.send_keys(pwd)
        btn = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
        btn.click()
        time.sleep(3)
        return "Spotify" in driver.title
    except TimeoutException:
        return False

# ───────────────────────────────────────────────────
# 3b) 차단 시 우회 로그인
# ───────────────────────────────────────────────────
def fallback_login(driver, user, pwd):
    wait = WebDriverWait(driver, 10)
    driver.get("https://accounts.spotify.com/ko/login?continue=https%3A%2F%2Fcharts.spotify.com/login")
    user_in = wait.until(EC.presence_of_element_located((By.ID, "login-username")))
    user_in.clear(); user_in.send_keys(user)
    cont = wait.until(EC.element_to_be_clickable((By.ID, "login-button"))); cont.click()
    pwd_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., '비밀번호로 로그인하기')]")))
    pwd_btn.click()
    time.sleep(1)
    pwd_in = wait.until(EC.presence_of_element_located((By.ID, "login-password")))
    pwd_in.clear(); pwd_in.send_keys(pwd)
    final = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    final.click()
    wait.until(EC.title_contains("Spotify"))

# ───────────────────────────────────────────────────
# 4) 수집할 날짜 리스트 계산
# ───────────────────────────────────────────────────
def get_next_dates(csv_path: str) -> list[str]:
    if os.path.exists(csv_path):
        df    = pd.read_csv(csv_path, parse_dates=["date"])
        start = df["date"].max() + timedelta(days=1)
    else:
        start = datetime(2025, 4, 28)
    cutoff = datetime.today().date() - timedelta(days=2)

    dates = []
    current = start
    while current.date() <= cutoff:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

# ───────────────────────────────────────────────────
# 5) 차트 페이지 접속 → CSV 다운로드
# ───────────────────────────────────────────────────
def download_chart(driver, date_str: str):
    wait = WebDriverWait(driver, 10)
    url  = f"https://charts.spotify.com/charts/view/regional-us-daily/{date_str}"
    print(f"▶ {date_str} 접속")
    driver.get(url)
    btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-encore-id='buttonTertiary']")))
    btn.click()
    time.sleep(3)

# ───────────────────────────────────────────────────
# 6) 통합본에 append (파일명→date 칼럼 삽입)
# ───────────────────────────────────────────────────
def append_new_data(csv_path: str, download_folder: str):
    df_exist    = pd.read_csv(csv_path, dtype={"date": str}) if os.path.exists(csv_path) else pd.DataFrame()
    new_frames  = []
    pattern     = os.path.join(download_folder, "regional-us-daily-*.csv")

    for fp in glob.glob(pattern):
        fname = os.path.basename(fp)
        m = re.search(r"regional-us-daily-(\d{4}-\d{2}-\d{2})\.csv", fname)
        if not m:
            continue
        date_str = m.group(1)
        df_new   = pd.read_csv(fp)
        df_new.insert(0, "date", date_str)
        new_frames.append(df_new)

    if not new_frames:
        print("🚫 추가할 데이터가 없습니다.")
        return

    df_all = pd.concat([df_exist] + new_frames, ignore_index=True)
    df_all.drop_duplicates(subset=["date", "rank", "uri"], inplace=True)
    df_all.to_csv(csv_path, index=False)
    added = sum(len(f) for f in new_frames)
    print(f"📝 {added}개 레코드 추가 후 저장: {csv_path}")

# ───────────────────────────────────────────────────
# 7) 메인 실행 (순서 변경)
# ───────────────────────────────────────────────────
if __name__ == "__main__":
    USER, PWD = "ks@rootnglobal.com", "jang4983!!"

    # 1) 수집 대상 날짜 우선 계산
    dates = get_next_dates(CSV_PATH)
    if not dates:
        print("✅ 이미 최신까지 수집 완료되었습니다.")
        exit(0)

    print(f"📅 수집 대상 날짜: {dates}")

    # 2) 로그인 & 다운로드
    driver = init_driver()
    if not try_simple_login(driver, USER, PWD):
        print("🔒 간단 로그인 실패, 우회 로그인 수행")
        fallback_login(driver, USER, PWD)
    else:
        print("✅ 간단 로그인 성공")

    for d in dates:
        download_chart(driver, d)
    driver.quit()

    # 3) 통합본 업데이트
    append_new_data(CSV_PATH, DOWNLOAD_FOLDER)