import pandas as pd

PATH = "data/parking_raw.csv"
CLEAN_PATH = "data/parking_clean.csv"
SHOW = ["주차장명", "소재지도로명주소", "위도", "경도", "주차기본요금"]  # 파일에 실제로 있는 칸 이름
AREA = "경상남도 김해시"  # 시·도까지 붙여 거름 ("김해"만 쓰면 다른 곳이 섞일 수 있음)
KEEP = ["주차장명", "주차장구분", "주차장유형", "소재지도로명주소", "소재지지번주소", "주차구획수",
        "주차기본시간", "주차기본요금", "요금정보", "위도", "경도", "데이터기준일자"]


def read_csv_kr(path):
    """utf-8-sig → cp949 순서로 읽어 (DataFrame, 인코딩) 을 돌려준다. 공공데이터는 둘 다 있음."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            # low_memory=False: 큰 파일을 나눠 읽다 한 칸에 숫자·글자가 섞였다고 경고하는 것 방지
            return pd.read_csv(path, encoding=enc, low_memory=False), enc
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"⛔ {path} 를 utf-8, cp949 둘 다로 읽지 못했어요")


def pick_area(df, area=AREA):
    """'주소'(도로명, 없으면 지번)에 area 가 들어간 줄만, KEEP 칸 + '주소' 칸으로 돌려준다.
    요금정보가 '무료'인 곳은 비어 있는 주차기본요금을 0 으로 채운다."""
    out = df[KEEP].copy()
    out["주소"] = out["소재지도로명주소"].fillna(out["소재지지번주소"])
    out.loc[out["요금정보"] == "무료", "주차기본요금"] = 0
    return out[out["주소"].str.contains(area, na=False, regex=False)]


if __name__ == "__main__":
    df, enc = read_csv_kr(PATH)
    print(f"인코딩: {enc}")
    print(f"{df.shape[0]:,}줄 × {df.shape[1]}칸")
    print("\n칸별 빈칸 개수:")
    print(df.isna().sum().to_string())
    print(f"\n칸 이름 전체 ({df.shape[1]}개):")
    print(", ".join(df.columns))
    print("\n처음 5줄:")
    print(df[SHOW].head(5).to_string())
    print(f"\n고른 칸 빈칸 개수 (전체 {len(df):,}줄 중):")
    print(df[SHOW].isna().sum().to_string())

    area = pick_area(df)
    print(f"\n'{AREA}' 주차장: {len(area)}곳 ({area.shape[1]}칸)")
    print(f"  조건: 소재지도로명주소(비었으면 소재지지번주소)에 '{AREA}' 가 들어 있음")
    print(area[["주차장명", "주소", "위도", "경도", "주차기본요금"]].head(5).to_string())

    # utf-8-sig: 파일 앞에 BOM 표시를 붙여 엑셀이 UTF-8 로 알아보게 (그냥 utf-8 이면 엑셀에서 한글이 깨짐)
    area.to_csv(CLEAN_PATH, encoding="utf-8-sig", index=False)
    print(f"\n{CLEAN_PATH} 에 {len(area)}줄 저장했어요 (인코딩 utf-8-sig)")
    print(f"\n출처: {PATH}, 데이터 기준일 {area['데이터기준일자'].min()} ~ {area['데이터기준일자'].max()}")
