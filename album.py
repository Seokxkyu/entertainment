import os
import time
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ────────────────────────────────────────────────────
# 1) 설정
# ────────────────────────────────────────────────────
CHROMEDRIVER_PATH = r"C:\Users\rootn\OneDrive\Desktop\intern\chromedriver-win32\chromedriver-win32\chromedriver.exe"
MERGED_CSV        = os.path.join(os.getcwd(), "data", "album_sales.csv")
BASE_URL          = "https://circlechart.kr/page_chart/album.circle"

# ────────────────────────────────────────────────────
# 2) WebDriver 초기화
# ────────────────────────────────────────────────────
def init_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)

# ────────────────────────────────────────────────────
# 3) 기존 merged CSV 에서 마지막 수집 월(YYYY-MM) 찾기
# ────────────────────────────────────────────────────
def get_last_month(merged_csv: str):
    if not os.path.exists(merged_csv):
        # 파일 자체가 없으면, 예시로 2015-01부터 수집 시작
        return datetime(2015, 1, 1)
    df = pd.read_csv(merged_csv, parse_dates=["Date"])
    last_date = df["Date"].max()
    # 마지막 월의 1일로 정제
    return last_date.replace(day=1)

# ────────────────────────────────────────────────────
# 4) 수집 대상 월 리스트 만들기
# ────────────────────────────────────────────────────
def build_target_months(start_month: datetime):
    last_collectable = datetime.today().replace(day=1) - relativedelta(months=1)
    months = []
    cur = start_month + relativedelta(months=1)
    while cur <= last_collectable:
        months.append((cur.year, cur.month))
        cur += relativedelta(months=1)
    return months
# ────────────────────────────────────────────────────
# 5) 한 달치 원시 테이블 크롤링
# ────────────────────────────────────────────────────
def crawl_month(year: int, month: int, driver):
    url = (
        f"{BASE_URL}"
        f"?nationGbn=K&targetTime={month:02d}"
        f"&hitYear={year}&termGbn=month&yearTime=3"
    )
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.ID, "pc_chart_tbody")))
    rows = driver.find_elements(By.CSS_SELECTOR, "#pc_chart_tbody tr")
    recs = []
    for tr in rows:
        cols = tr.find_elements(By.TAG_NAME, "td")
        if len(cols) < 5:
            continue
        recs.append({
            "Album_Info":  cols[2].text.strip(),
            "Play_Count":  cols[3].text.strip()
        })
    return pd.DataFrame(recs)

# ────────────────────────────────────────────────────
# 6) 새로운 월별 데이터를 기존 merged 에 증분 반영
# ────────────────────────────────────────────────────
def incremental_update(merged_csv: str, driver):
    """
    merged_csv: 기존 album_sales.csv 경로
    driver: Selenium WebDriver 인스턴스
    """
    if os.path.exists(merged_csv):
        df_merged = pd.read_csv(merged_csv, parse_dates=["Date"])
    else:
        df_merged = pd.DataFrame(columns=[
            "Artist", "Album", "Year", "Month", "Sales", "Year_Month", "Date"
        ])

    last_month = get_last_month(merged_csv)            
    targets    = build_target_months(last_month)        
    if not targets:
        print("✅ 이미 최신까지 수집 완료.")
        return

    print("📅 증분 수집 대상 월:", targets)

    for year, month in targets:
        print(f"▶ 크롤링 {year}-{month:02d}")
        df_raw = crawl_month(year, month, driver)  
        if df_raw.empty:
            continue

        df_raw[["Album","Artist"]] = df_raw["Album_Info"].str.split("\n", expand=True)
        df_raw[["Sales","_"]]       = df_raw["Play_Count"].str.split(" / ", expand=True)
        df_raw["Sales"]             = df_raw["Sales"].str.replace(",", "").astype(int)

        df_raw["Album"] = df_raw["Album"].str.replace(r"\s*\(.*\)", "", regex=True).str.strip()
        df_monthly = df_raw.groupby(["Artist","Album"], as_index=False)["Sales"].sum()

        df_monthly["Year"]  = year
        df_monthly["Month"] = month

        for _, row in df_monthly.iterrows():
            mask = (
                (df_merged["Artist"] == row["Artist"]) &
                (df_merged["Album"]  == row["Album"])
            )
            if mask.any():
                df_merged.loc[mask, "Sales"] += row["Sales"]
            else:
                new = {
                    "Artist": row["Artist"],
                    "Album":  row["Album"],
                    "Year":   row["Year"],
                    "Month":  row["Month"],
                    "Sales":  row["Sales"]
                }
                df_merged = pd.concat([df_merged, pd.DataFrame([new])], ignore_index=True)

        time.sleep(1)

    df_merged["Year_Month"] = (
        df_merged["Year"].astype(str)
        + "-"
        + df_merged["Month"].astype(str).str.zfill(2)
    )
    df_merged["Date"] = (
        pd.PeriodIndex(df_merged["Year_Month"], freq="M")
          .to_timestamp(how="end")
          .normalize()
    )

    df_merged.to_csv(merged_csv, index=False, encoding="utf-8-sig")
    print(f"📝 {len(targets)}개 월 증분 반영 완료 → {merged_csv}")


# ────────────────────────────────────────────────────
# 7) main
# ────────────────────────────────────────────────────
def main():
    driver = init_driver()
    try:
        incremental_update(MERGED_CSV, driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()