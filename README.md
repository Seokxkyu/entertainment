# 음악 산업 데이터 업데이트

## 📂 디렉토리 구조
```bash
intern/                           
└── entertainment/                
    ├── data/
    │   ├── us_weekly_yt.csv
    │   ├── ytweekly/             
    │   │   └── youtube-charts-top-artists-us-weekly-YYYYMMDD
    │   ├── spotdaily/             
    │   │   └── regional-us-daily-YYYY-MM-DD.csv
    │   ├── us_daily_stream.csv   
    │   └── album_merged.csv       
    ├── album.py                   
    ├── spotify.py                 
    └── youtube_music.py           
```

## 모듈 구성
- **album.py** : 써클차트에서 월간 앨범 차트 데이터를 수집
- **spotify.py** : 스포티파이의 일간 스트리밍 차트 데이터를 수집
- **youtube_music.py** : 유튜브뮤직의 월간 아티스트 데이터를 수집

## 사용법
### 1. 앨범 판매량 (Monthly)
```bash
cd intern/entertainment
python album.py
```

### 2. 스포티파이 스트리밍 수 (Daily)
```bash
cd intern/entertainment
python spotify.py
```

### 3. 유튜브뮤직 아티스트 차트 (Weekly)
```bash
cd intern/entertainment
python youtube_music.py
```