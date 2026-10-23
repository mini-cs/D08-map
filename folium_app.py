import html
import os

import folium
import streamlit as st
from dotenv import load_dotenv

from geo import _kakao_get  # 키 읽기·에러 처리는 geo.py 한 곳에서
from place import search_place

# 🔌 API 주소는 여기 한 곳에만 (장소 검색 주소는 place.py 의 API)
API = {
    "category": "https://dapi.kakao.com/v2/local/search/category.json",
}
CATEGORIES = {
    "카페": "CE7", "음식점": "FD6", "편의점": "CS2", "약국": "PM9", "병원": "HP8", "지하철역": "SW8",
    "주차장": "PK6", "대형마트": "MT1", "은행": "BK9", "관광명소": "AT4", "문화시설": "CT1",
}


@st.cache_data(ttl=600)
def find_center(query):
    """검색어로 찾은 첫 장소 {"이름", "주소", "위도", "경도"} 또는 None. 에러는 예외로 (캐시 안 됨)."""
    places = search_place(query, n=1)
    return places[0] if places else None


@st.cache_data(ttl=600)
def nearby(code, 위도, 경도, radius):
    """(위도, 경도) 반경 radius(m) 안 카테고리 장소를 가까운 순으로 최대 15개."""
    docs = _kakao_get(API["category"], {
        "category_group_code": code,
        "x": 경도, "y": 위도,  # 요청은 x=경도, y=위도
        "radius": radius,
        "sort": "distance",
        "size": 15,
    })
    rows = []
    for d in docs:
        위도_, 경도_ = float(d["y"]), float(d["x"])  # 카카오: y=위도, x=경도 (글자)
        if not (33 <= 위도_ <= 39 and 124 <= 경도_ <= 132):
            continue  # 한국 밖 좌표는 잘못된 값
        rows.append({
            "이름": d["place_name"],
            "주소": d.get("road_address_name") or d["address_name"],
            "거리(m)": int(d["distance"]) if d.get("distance") else None,
            "위도": 위도_,
            "경도": 경도_,
        })
    return rows


def popup(name, address):
    # 이름에 태그·따옴표가 있어도 지도가 안 깨지게 (folium Popup 은 기본이 HTML 그대로)
    return folium.Popup(f"<b>{html.escape(name)}</b><br>{html.escape(address)}", max_width=250)


st.set_page_config(page_title="동네 장소 지도", page_icon="🗺️")
st.title("동네 장소 지도")

load_dotenv(override=True)
if not os.getenv("KAKAO_REST_API_KEY"):
    st.error(".env 에 KAKAO_REST_API_KEY 가 없어요. 키를 넣고 Ctrl+C 후 다시 streamlit run 해 주세요")
    st.stop()

with st.sidebar:
    query = st.text_input("기준 장소", "김해 신문동")
    category = st.selectbox("카테고리", list(CATEGORIES))
    radius = st.slider("반경 (m)", 100, 3000, 1000, step=100)

if not query.strip():
    st.info("기준 장소를 입력해 주세요")
    st.stop()

try:
    center = find_center(query.strip())
    if center is None:
        st.info(f"'{query}'을(를) 찾지 못했어요")
        st.stop()
    rows = nearby(CATEGORIES[category], center["위도"], center["경도"], radius)
except RuntimeError as e:
    st.error(str(e))
    st.stop()

st.caption(f"기준: {center['이름']} ({center['주소']}) · 반경 {radius}m 안 {category} {len(rows)}곳 (가까운 순, 최대 15곳)")

m = folium.Map(location=[center["위도"], center["경도"]], zoom_start=15)
folium.Circle([center["위도"], center["경도"]], radius=radius, color="#1e88e5", fill=False).add_to(m)
folium.Marker(
    [center["위도"], center["경도"]],
    popup=popup(f"기준: {center['이름']}", center["주소"]),
    icon=folium.Icon(color="red", icon="star"),
).add_to(m)
for r in rows:
    folium.Marker(
        [r["위도"], r["경도"]],
        popup=popup(r["이름"], f"{r['주소']} · {r['거리(m)']}m"),
        icon=folium.Icon(color="blue"),
    ).add_to(m)
points = [[center["위도"], center["경도"]]] + [[r["위도"], r["경도"]] for r in rows]
if len(points) > 1:
    m.fit_bounds(points)

st.iframe(m.get_root().render(), height=500)

if rows:
    st.dataframe(rows, hide_index=True)
else:
    st.info("조건에 맞는 곳이 없어요")

st.caption("출처: 카카오 로컬 API (키워드로 장소 검색, 카테고리로 장소 검색) · 지도 © OpenStreetMap")
