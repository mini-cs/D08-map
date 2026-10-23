import html
import json
import os
import sys

from dotenv import load_dotenv

from place import search_place

MAX_MARKERS = 200  # 너무 많으면 지도가 느려짐


def kakao_map(js_key, places, height=500, legend=None):
    """[{"이름", "주소", "위도", "경도"}, ...] 를 마커로 찍은 카카오 지도 HTML 글자를 돌려준다.
    장소에 "색"(예: "#d32f2f")이 있으면 그 색 핀, 없으면 카카오 기본 마커.
    legend={"설명": "#색", ...} 을 주면 지도 오른쪽 위에 색 범례를 띄운다.
    js_key 는 JavaScript 키만. REST 키는 넣지 않는다."""
    # </script> 가 든 장소 이름이 script 태그를 닫지 못하게
    data = json.dumps(places[:MAX_MARKERS], ensure_ascii=False).replace("</", "<\\/")
    legend_box = ""
    if legend:
        rows = "".join(
            f'<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
            f'background:{html.escape(color)};margin-right:6px;vertical-align:-1px"></span>{html.escape(label)}</div>'
            for label, color in legend.items()
        )
        legend_box = (
            '<div style="position:absolute;top:10px;right:10px;z-index:10;background:#fff;color:#222;'
            'padding:8px 10px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.3);font-size:13px;line-height:1.7">'
            f"{rows}</div>"
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>장소 지도</title>
</head>
<body style="margin:0;font-family:sans-serif">
<div style="position:relative">
<div id="map" style="width:100%;height:{height}px"></div>
{legend_box}
</div>
<p style="margin:8px;font-size:14px;color:#555">
  지도가 회색이면: ① 카카오맵 사용 설정 ② 지금 주소(포트까지) 등록 ③ 서버 주소로 열기
</p>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={js_key}&autoload=false"></script>
<script>
const places = {data};
function pin(color) {{
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="40" viewBox="-2 -2 32 44">`
    + `<path d="M14 0C6.3 0 0 6.3 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.3 21.7 0 14 0z" `
    + `fill="${{color}}" stroke="#fff" stroke-width="2"/><circle cx="14" cy="14" r="5" fill="#fff"/></svg>`;
  return new kakao.maps.MarkerImage(
    "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg),
    new kakao.maps.Size(28, 40),
    {{ offset: new kakao.maps.Point(14, 40) }},  // 핀 끝이 좌표에 오게
  );
}}
kakao.maps.load(() => {{
  const map = new kakao.maps.Map(document.getElementById("map"), {{
    center: new kakao.maps.LatLng(places[0].위도, places[0].경도),
    level: 4,
  }});
  const bounds = new kakao.maps.LatLngBounds();
  let opened = null;
  for (const p of places) {{
    const pos = new kakao.maps.LatLng(p.위도, p.경도);
    const opts = {{ map, position: pos }};
    if (p.색) opts.image = pin(p.색);
    const marker = new kakao.maps.Marker(opts);
    // 이름·주소는 textContent 로 넣어 따옴표·태그가 있어도 안 깨지게
    const box = document.createElement("div");
    box.style.cssText = "padding:6px 8px;font-size:13px;width:220px";
    const name = document.createElement("b");
    name.textContent = p.이름;
    const addr = document.createElement("div");
    addr.style.whiteSpace = "pre-line";  // 주소 글자 속 줄바꿈을 화면에서도 줄바꿈으로
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
