import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

st.set_page_config(page_title="우리 학교 급식 식단표", page_icon="🍱", layout="centered")

st.markdown("""
<style>
.meal-card {
    background: linear-gradient(135deg, #43a047 0%, #a5d6a7 100%);
    border-radius: 20px;
    padding: 24px 22px;
    color: white;
    box-shadow: 0 8px 24px rgba(67,160,71,0.30);
    margin-bottom: 16px;
}
.meal-card .school {
    font-size: 14px;
    opacity: 0.9;
}
.meal-card .date {
    font-size: 26px;
    font-weight: 800;
    margin: 4px 0 2px 0;
}
.meal-card .sub {
    font-size: 13px;
    opacity: 0.9;
}
.dish-list {
    margin-top: 14px;
}
.dish-item {
    background: rgba(255,255,255,0.9);
    color: #222;
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 15px;
}
.dish-item .name {
    font-weight: 600;
}
.dish-item .allergy {
    font-size: 11px;
    color: #888;
    text-align: right;
}
.info-grid {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}
.info-box {
    flex: 1;
    background: #f7f7f9;
    border-radius: 14px;
    padding: 12px 8px;
    text-align: center;
}
.info-box .val {
    font-size: 18px;
    font-weight: 700;
    color: #222;
}
.info-box .lbl {
    font-size: 11px;
    color: #888;
}
</style>
""", unsafe_allow_html=True)

ALLERGY_MAP = {
    "1": "난류", "2": "우유", "3": "메밀", "4": "땅콩", "5": "대두",
    "6": "밀", "7": "고등어", "8": "게", "9": "새우", "10": "돼지고기",
    "11": "복숭아", "12": "토마토", "13": "아황산류", "14": "호두",
    "15": "닭고기", "16": "쇠고기", "17": "오징어", "18": "조개류(굴·전복·홍합 포함)",
    "19": "잣",
}

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


@st.cache_data
def load_data():
    with open("meal.json", encoding="utf-8") as f:
        raw = json.load(f)

    def is_valid(r):
        return bool(re.fullmatch(r"\d{8}", str(r.get("MLSV_YMD", ""))))

    rows = [r for r in raw if is_valid(r)]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["MLSV_YMD"], format="%Y%m%d")
    df["급식인원수"] = pd.to_numeric(df["MLSV_FGR"], errors="coerce")
    return df


def parse_dishes(ddish_nm):
    dishes = []
    for item in str(ddish_nm).split("<br/>"):
        item = item.strip()
        if not item:
            continue
        m = re.match(r"^(.*)\s\(([0-9.]+)\)$", item)
        if m:
            name, codes = m.group(1).strip(), m.group(2).split(".")
            allergy_names = [ALLERGY_MAP.get(c, c) for c in codes if c]
            dishes.append((name, allergy_names))
        else:
            dishes.append((item, []))
    return dishes


def parse_kv_block(text):
    result = []
    for item in str(text).split("<br/>"):
        if ":" in item:
            k, v = item.split(":", 1)
            result.append((k.strip(), v.strip()))
    return result


def parse_calorie(cal_info):
    m = re.search(r"[\d.]+", str(cal_info))
    return float(m.group()) if m else None


df = load_data()

st.title("🍱 우리 학교 급식 식단표")

if df.empty:
    st.warning("불러올 수 있는 급식 데이터가 없습니다. meal.json 파일을 확인해 주세요.")
    st.stop()

st.caption(f"교육부 나이스(NEIS) 급식 식단 정보 · 총 {len(df)}건의 급식 기록")

schools = sorted(df["SCHUL_NM"].unique())
if len(schools) > 1:
    school = st.selectbox("🏫 학교 선택", schools)
else:
    school = schools[0]
    st.markdown(f"**🏫 {school}**")

df_school = df[df["SCHUL_NM"] == school]

available_dates = sorted(df_school["날짜"].unique())
default_idx = len(available_dates) - 1

date_labels = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in available_dates]
selected_label = st.selectbox("📅 날짜 선택", date_labels, index=default_idx)
selected_date = pd.Timestamp(selected_label)

df_day = df_school[df_school["날짜"] == selected_date]

meal_types = df_day["MMEAL_SC_NM"].unique().tolist()
if len(meal_types) > 1:
    meal_type = st.radio("🍽️ 식사 선택", meal_types, horizontal=True)
else:
    meal_type = meal_types[0]

row = df_day[df_day["MMEAL_SC_NM"] == meal_type].iloc[0]

dishes = parse_dishes(row["DDISH_NM"])
origins = parse_kv_block(row.get("ORPLC_INFO", ""))
nutrients = parse_kv_block(row.get("NTR_INFO", ""))
calorie = parse_calorie(row.get("CAL_INFO", ""))

weekday = WEEKDAY_KR[selected_date.weekday()]

st.markdown(f"""
<div class="meal-card">
    <div class="school">{school}</div>
    <div class="date">{selected_date.strftime('%Y년 %m월 %d일')} ({weekday})</div>
    <div class="sub">{meal_type} · 급식인원 {int(row['급식인원수']) if pd.notna(row['급식인원수']) else '-'}명</div>
</div>
""", unsafe_allow_html=True)

st.markdown("##### 🍚 오늘의 메뉴")
dish_html = '<div class="dish-list">'
for name, allergies in dishes:
    allergy_str = " · ".join(allergies) if allergies else ""
    dish_html += f"""
    <div class="dish-item">
        <span class="name">{name}</span>
        <span class="allergy">{allergy_str}</span>
    </div>
    """
dish_html += "</div>"
st.markdown(dish_html, unsafe_allow_html=True)

carb = next((v for k, v in nutrients if "탄수화물" in k), None)
protein = next((v for k, v in nutrients if "단백질" in k), None)
fat = next((v for k, v in nutrients if "지방" in k), None)

st.markdown(f"""
<div class="info-grid">
    <div class="info-box">
        <div class="val">{calorie:.0f}</div>
        <div class="lbl">칼로리(Kcal)</div>
    </div>
    <div class="info-box">
        <div class="val">{carb or '-'}</div>
        <div class="lbl">탄수화물(g)</div>
    </div>
    <div class="info-box">
        <div class="val">{protein or '-'}</div>
        <div class="lbl">단백질(g)</div>
    </div>
    <div class="info-box">
        <div class="val">{fat or '-'}</div>
        <div class="lbl">지방(g)</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("🌱 원산지 정보 보기"):
    if origins:
        origin_df = pd.DataFrame(origins, columns=["재료", "원산지"])
        st.dataframe(origin_df, use_container_width=True, hide_index=True)
    else:
        st.write("원산지 정보가 없습니다.")

with st.expander("📊 상세 영양 정보 보기"):
    if nutrients:
        nutrient_df = pd.DataFrame(nutrients, columns=["영양소", "함량"])
        st.dataframe(nutrient_df, use_container_width=True, hide_index=True)
    else:
        st.write("영양 정보가 없습니다.")

st.markdown("&nbsp;")
st.markdown("##### ⚠️ 알레르기 유발 식품 안내")
st.caption("메뉴 옆 숫자는 아래 알레르기 유발물질 코드에 해당합니다.")
legend = " · ".join([f"{k}.{v}" for k, v in ALLERGY_MAP.items()])
st.caption(legend)
