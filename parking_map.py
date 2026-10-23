import os
import sys

from dotenv import load_dotenv

from make_map import kakao_map
from parking import CLEAN_PATH, read_csv_kr

if __name__ == "__main__":
    load_dotenv()
    js_key = os.getenv("KAKAO_JS_KEY")
    if not js_key:
        print("⛔ .env 에 KAKAO_JS_KEY 가 없어요")
        sys.exit(1)
    if js_key == os.getenv("KAKAO_REST_API_KEY"):
        print("⛔ KAKAO_JS_KEY 에 REST 키가 들어 있어요. JavaScript 키를 넣어 주세요")
        sys.exit(1)

    try:
        df, enc = read_csv_kr(CLEAN_PATH)
    except (OSError, RuntimeError) as e:
        print(f"⛔ {CLEAN_PATH} 를 읽지 못했어요. 먼저 python parking.py 를 실행해 주세요 ({e})")
        sys.exit(1)

    free = df[df["요금정보"] == "무료"]
    # 한국 밖 좌표(뒤바뀐 좌표·0 좌표)는 지도에 안 찍음
    free = free[free["위도"].between(33, 39) & free["경도"].between(124, 132)]
    print(f"{CLEAN_PATH} ({enc}) {len(df)}곳 중 무료 주차장 {len(free)}곳")
    print("  조건: 요금정보 == '무료' 이고 위도 33~39, 경도 124~132 안")
    if free.empty:
        print("조건에 맞는 곳이 없어요")
        sys.exit(1)

    markers = [
        {
            "이름": r.주차장명,
            "주소": f"유형: {r.주차장유형}\n기본요금: {r.주차기본요금:,.0f}원 (무료)",  # 정보창 둘째 줄
            "위도": r.위도,
            "경도": r.경도,
        }
        for r in free.itertuples()
    ]
    with open("map.html", "w", encoding="utf-8") as f:
        f.write(kakao_map(js_key, markers))
    print(f"\nmap.html 에 마커 {len(markers)}개를 찍었어요")
    print("열기: 이 폴더에서 python -m http.server 8000 --bind 127.0.0.1 → http://localhost:8000/map.html")
    print(f"\n출처: {CLEAN_PATH} (원본 data/parking_raw.csv), 데이터 기준일 {df['데이터기준일자'].max()}")
