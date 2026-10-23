import os
import sys

import requests
from dotenv import load_dotenv

# 🔌 API 주소는 여기 한 곳에만
API = {
    "address": "https://dapi.kakao.com/v2/local/search/address.json",
    "coord2address": "https://dapi.kakao.com/v2/local/geo/coord2address.json",
}


def _kakao_get(url, params):
    """카카오 로컬 API를 불러 documents 목록을 돌려준다. 키·설정·연결 문제는 '⛔' RuntimeError."""
    load_dotenv()
    key = os.getenv("KAKAO_REST_API_KEY")
    if not key:
        raise RuntimeError("⛔ .env 에 KAKAO_REST_API_KEY 가 없어요")

    try:
        res = requests.get(  # 🔌 API 호출
            url,
            headers={"Authorization": f"KakaoAK {key}"},
            params=params,
            timeout=10,
        )
    except requests.RequestException:
        raise RuntimeError("⛔ 카카오 서버에 연결하지 못했어요 (인터넷 확인)") from None

    if res.status_code == 401:
        raise RuntimeError("⛔ 카카오 REST API 키가 틀렸어요")
    if res.status_code == 403:
        raise RuntimeError("⛔ 카카오맵 사용 설정을 켜 주세요")
    if res.status_code != 200:
        raise RuntimeError(f"⛔ 카카오 요청 실패 (상태 코드 {res.status_code})")
    return res.json().get("documents", [])


def address_to_coord(address):
    """주소 → (위도, 경도). 못 찾거나 한국 밖 좌표면 None."""
    docs = _kakao_get(API["address"], {"query": address})
    if not docs:
        return None
    위도, 경도 = float(docs[0]["y"]), float(docs[0]["x"])  # 카카오: y=위도, x=경도 (글자)
    if not (33 <= 위도 <= 39 and 124 <= 경도 <= 132):
        return None  # 한국 밖 좌표는 잘못된 값
    return 위도, 경도


def coord_to_address(위도, 경도):
    """(위도, 경도) → 도로명 주소, 도로명이 없으면 지번 주소. 못 찾으면 None."""
    docs = _kakao_get(API["coord2address"], {"x": 경도, "y": 위도})  # 요청은 x=경도, y=위도
    if not docs:
        return None
    road = docs[0].get("road_address")  # 산·공원 등은 null
    if road:
        return road["address_name"]
    return docs[0]["address"]["address_name"]


if __name__ == "__main__":
    address = " ".join(sys.argv[1:]) or input("주소 (예: 김해시 신문동): ").strip()
    try:
        coord = address_to_coord(address)
        if coord is None:
            print(f"'{address}'을(를) 찾지 못했어요")
            sys.exit(1)
        print(f"1) {address} → (위도, 경도) = {coord}")
        print(f"2) {coord} → 주소 = {coord_to_address(*coord) or '주소를 찾지 못했어요'}")
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    print("\n출처: 카카오 로컬 API (주소로 좌표 변환, 좌표로 주소 변환)")
