import os
import sys

import requests
from dotenv import load_dotenv

# 🔌 API 주소는 여기 한 곳에만
API = {
    "keyword": "https://dapi.kakao.com/v2/local/search/keyword.json",
}


def search_place(query, n=5):
    """검색어로 장소를 찾아 [{"이름", "주소", "위도", "경도"}, ...] 를 최대 n개 돌려준다.
    키·설정·연결 문제는 '⛔'로 시작하는 RuntimeError, 결과가 없으면 빈 목록."""
    load_dotenv()
    key = os.getenv("KAKAO_REST_API_KEY")
    if not key:
        raise RuntimeError("⛔ .env 에 KAKAO_REST_API_KEY 가 없어요")

    try:
        res = requests.get(  # 🔌 API 호출
            API["keyword"],
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": query, "size": 15},
            timeout=10,
        )
    except requests.RequestException:
        raise RuntimeError("⛔ 카카오 서버에 연결하지 못했어요 (인터넷 확인)") from None

    if res.status_code == 401:
        raise RuntimeError("⛔ 카카오 REST API 키가 틀렸어요")
    if res.status_code == 403:
        raise RuntimeError("⛔ 카카오맵 사용 설정을 켜 주세요")
    if res.status_code != 200:
        raise RuntimeError(f"⛔ 카카오 검색 실패 (상태 코드 {res.status_code})")

    places = []
    for d in res.json().get("documents", []):
        위도, 경도 = float(d["y"]), float(d["x"])  # 카카오: y=위도, x=경도 (글자)
        if not (33 <= 위도 <= 39 and 124 <= 경도 <= 132):
            continue  # 한국 밖 좌표는 잘못된 값
        places.append({
            "이름": d["place_name"],
            "주소": d.get("road_address_name") or d["address_name"],
            "위도": 위도,
            "경도": 경도,
        })
        if len(places) == n:
            break
    return places


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or input("검색어 (예: 신문동 카페): ").strip()
    try:
        places = search_place(query)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    if not places:
        print(f"'{query}'을(를) 찾지 못했어요")
    for i, p in enumerate(places, 1):
        print(f"{i}. {p['이름']}, {p['주소']}, ({p['위도']}, {p['경도']})")
    print("\n출처: 카카오 로컬 API (키워드로 장소 검색)")
