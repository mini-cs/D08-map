import os
import re
import sys
import time

from dotenv import load_dotenv

from geo import address_forms, address_to_coord
from make_map import kakao_map
from place import search_place

# 이름 뒤 구분자: " | " 또는 " : "
SPLIT = re.compile(r"\s*\|\s*|\s+:\s+")
HEADER_NAMES = {"이름", "가게이름", "가게 이름", "상호", "장소"}
MARK_COLOR = {"✅": "#2e7d32", "🟡": "#f9a825", "❌": "#d32f2f"}  # 지도 핀 색: 초록·노랑·빨강
MARK_LABEL = {"✅": "이름·주소 맞음", "🟡": "주소 다름 / 이름 일부만 같음", "❌": "못 찾음 (AI 주소 위치)"}
# 주소에서 비교할 낱말: 시·군·구·동·읍·면·리·로·길·가 로 끝나는 것 (번지·"일원"은 뺌)
AREA_WORD = re.compile(r"(시|군|구|동|읍|면|리|로|길|가)$")


def read_lines(path):
    """utf-8-sig → cp949 순서로 읽고, 어떤 인코딩이었는지 함께 돌려준다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc) as f:
                return f.read().splitlines(), enc
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"⛔ {path} 를 읽지 못했어요 (utf-8, cp949 둘 다 실패)")


def parse_line(line):
    """'1. 이름 | 주소', '• 이름 : 주소', '| 이름 | 주소 |' → (이름, 주소). 읽을 줄이 아니면 None."""
    line = line.strip()
    if not line or set(line) <= set("|-: "):  # 빈 줄, 표 구분선 | --- |
        return None
    line = re.sub(r"^([•\-*]|\d+[.)])\s*", "", line).strip("| ")  # 번호·글머리·표 테두리
    parts = SPLIT.split(line, maxsplit=1)
    if len(parts) != 2 or parts[0] in HEADER_NAMES:
        return None
    return parts[0].strip(), parts[1].strip()


def area_words(address):
    """주소 첫 단어(서울특별시/서울, 경상남도/경남)는 빼고 시·구·동·로·길 낱말만 모은다."""
    words = [w.strip("(),") for w in address.split()[1:]]
    return {w for w in words if AREA_WORD.search(w)}


def same_name(a, b):
    return a.replace(" ", "").lower() == b.replace(" ", "").lower()


def judge(name, address, places):
    """✅ 이름 같고 구·동(길) 맞음 / 🟡 이름 같고 주소 다름, 또는 이름 일부만 같고 주소 맞음 / ❌ 못 찾음.
    (판정, 맞춘 카카오 장소)"""
    wants = [area_words(address)]
    looked_up = False

    def addr_ok(p):
        nonlocal looked_up
        # 카카오 도로명·지번 둘 중 어느 쪽 표기로 써도 맞게
        have = area_words(p["주소"]) | area_words(p["지번주소"])
        if any(w and w <= have for w in wants):
            return True
        if not looked_up:
            # AI가 도로명으로, 카카오는 지번으로만 적었을 수 있음 → AI 주소의 다른 표기를 한 번만 받아 다시 비교
            looked_up = True
            wants.extend(area_words(a) for a in address_forms(address))
            return any(w and w <= have for w in wants)
        return False

    named = [p for p in places if same_name(p["이름"], name)]
    if not named:
        # 첫 단어(브랜드)가 같고 주소도 맞으면 같은 가게로 봄 (예: 캘리클럽 김해점 ↔ 캘리클럽 유니버스플루토 김해점)
        partial = [p for p in places
                   if p["이름"].lower().split()[:1] == name.lower().split()[:1] and addr_ok(p)]
        return ("🟡", partial[0]) if partial else ("❌", None)
    for p in named:
        if addr_ok(p):
            return "✅", p
    return "🟡", named[0]


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "1.txt"
    try:
        lines, enc = read_lines(path)
    except (OSError, RuntimeError) as e:
        print(e)
        sys.exit(1)
    rows = [r for r in map(parse_line, lines) if r]
    print(f"{path} 를 {enc} 로 읽었어요: 확인할 줄 {len(rows)}개\n")

    counts = {"✅": 0, "🟡": 0, "❌": 0}
    markers = []
    for i, (name, address) in enumerate(rows, 1):
        town = address.split()[1] if len(address.split()) > 1 else ""  # 동네 = 주소 둘째 단어 (김해시, 강남구)
        try:
            places = search_place(f"{town} {name}".strip(), n=15)
            mark, found = judge(name, address, places)
            # ❌ 는 카카오 장소가 없으니 AI가 적은 주소 위치에 찍음
            coord = (found["위도"], found["경도"]) if found else address_to_coord(address)
        except RuntimeError as e:
            print(e)  # 키·설정·연결 문제는 바로 멈춤
            sys.exit(1)
        counts[mark] += 1
        print(f"{i}. {mark} {name} | {address}")
        if found:
            print(f"      카카오: {found['이름']} | {found['주소']} (지번 {found['지번주소']})")
        if coord:
            where = f"카카오: {found['이름']} · {found['주소']}" if found else f"AI 주소 위치: {address}"
            markers.append({"이름": f"{i}. {mark} {name}", "주소": where, "위도": coord[0], "경도": coord[1],
                            "색": MARK_COLOR[mark]})
        time.sleep(0.1)

    total = len(rows)
    wrong = counts["🟡"] + counts["❌"]
    print(f"\n✅ {counts['✅']}개 · 🟡 {counts['🟡']}개 · ❌ {counts['❌']}개 (총 {total}개)")
    if total:
        print(f"AI 실수율 = (🟡 + ❌) / 전체 = {wrong}/{total} = {wrong / total:.0%}")
    print("판정 기준: 띄어쓰기 뺀 이름이 같고, 주소 첫 단어를 뺀 시·구·동·로·길 낱말이 카카오 도로명/지번 주소에 모두 있으면 ✅, 이름 첫 단어만 같고 주소가 맞으면 🟡")
    print("          (AI 주소가 도로명/지번 중 다른 표기여도 카카오 '주소로 좌표 변환'으로 두 표기를 받아 비교)")

    load_dotenv()
    js_key = os.getenv("KAKAO_JS_KEY")
    if not js_key:
        print("\n⛔ .env 에 KAKAO_JS_KEY 가 없어서 지도는 만들지 않았어요")
    elif js_key == os.getenv("KAKAO_REST_API_KEY"):
        print("\n⛔ KAKAO_JS_KEY 에 REST 키가 들어 있어요. 지도는 만들지 않았어요")
    elif markers:
        with open("map.html", "w", encoding="utf-8") as f:
            legend = {f"{m} {MARK_LABEL[m]} ({counts[m]}개)": MARK_COLOR[m] for m in MARK_COLOR}
            f.write(kakao_map(js_key, markers, legend=legend))
        print(f"\nmap.html 에 마커 {len(markers)}개를 찍었어요 (마커를 누르면 판정이 보여요)")
        print("열기: 이 폴더에서 python -m http.server 8000 --bind 127.0.0.1 → http://localhost:8000/map.html")
    print("\n출처: 카카오 로컬 API (키워드로 장소 검색, 주소로 좌표 변환)")
