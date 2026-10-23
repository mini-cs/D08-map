import json
import os
import sys

from dotenv import load_dotenv

from place import search_place

MAX_MARKERS = 200  # 너무 많으면 지도가 느려짐


def kakao_map(js_key, places, height=500):
    """[{"이름", "주소", "위도", "경도"}, ...] 를 마커로 찍은 카카오 지도 HTML 글자를 돌려준다.
    js_key 는 JavaScript 키만. REST 키는 넣지 않는다."""
    # </script> 가 든 장소 이름이 script 태그를 닫지 못하게
    data = json.dumps(places[:MAX_MARKERS], ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>장소 지도</title>
</head>
<body style="margin:0;font-family:sans-serif">
<div id="map" style="width:100%;height:{height}px"></div>
<p style="margin:8px;font-size:14px;color:#555">
  지도가 회색이면: ① 카카오맵 사용 설정 ② 지금 주소(포트까지) 등록 ③ 서버 주소로 열기
</p>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={js_key}&autoload=false"></script>
<script>
const places = {data};
kakao.maps.load(() => {{
  const map = new kakao.maps.Map(document.getElementById("map"), {{
    center: new kakao.maps.LatLng(places[0].위도, places[0].경도),
    level: 4,
  }});
  const bounds = new kakao.maps.LatLngBounds();
  let opened = null;
  for (const p of places) {{
    const pos = new kakao.maps.LatLng(p.위도, p.경도);
    const marker = new kakao.maps.Marker({{ map, position: pos }});
    // 이름·주소는 textContent 로 넣어 따옴표·태그가 있어도 안 깨지게
    const box = document.createElement("div");
    box.style.cssText = "padding:6px 8px;font-size:13px;width:220px";
    const name = document.createElement("b");
    name.textContent = p.이름;
    const addr = document.createElement("div");
    addr.textContent = p.주소;
    box.append(name, addr);
    const info = new kakao.maps.InfoWindow({{ content: box, removable: true }});
    kakao.maps.event.addListener(marker, "click", () => {{
      if (opened) opened.close();
      info.open(map, marker);
      opened = info;
    }});
    bounds.extend(pos);
  }}
  map.setBounds(bounds);
}});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    load_dotenv()
    js_key = os.getenv("KAKAO_JS_KEY")
    if not js_key:
        print("⛔ .env 에 KAKAO_JS_KEY 가 없어요")
        sys.exit(1)
    if js_key == os.getenv("KAKAO_REST_API_KEY"):
        print("⛔ KAKAO_JS_KEY 에 REST 키가 들어 있어요. JavaScript 키를 넣어 주세요")
        sys.exit(1)

    query = " ".join(sys.argv[1:]) or input("검색어 (예: 신문동 카페): ").strip()
    try:
        places = search_place(query, n=10)
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    if not places:
        print(f"'{query}'을(를) 찾지 못했어요")
        sys.exit(1)

    with open("map.html", "w", encoding="utf-8") as f:
        f.write(kakao_map(js_key, places))
    for i, p in enumerate(places, 1):
        print(f"{i}. {p['이름']}, {p['주소']}, ({p['위도']}, {p['경도']})")
    print(f"\nmap.html 에 마커 {len(places)}개를 찍었어요")
    print("열기: 이 폴더에서 python -m http.server 8000 --bind 127.0.0.1 → http://localhost:8000/map.html")
    print("\n출처: 카카오 로컬 API (키워드로 장소 검색), 카카오 지도 JavaScript SDK")
