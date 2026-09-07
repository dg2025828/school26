import streamlit as st
import pandas as pd
import json
import re
from collections import Counter
from itertools import combinations

st.set_page_config(page_title="급식 메뉴 궁합 분석", page_icon="🍽️", layout="centered")

st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #ff6a88 0%, #ff9a8b 100%);
    border-radius: 20px;
    padding: 22px 22px;
    color: white;
    box-shadow: 0 8px 24px rgba(255,106,136,0.30);
    margin-bottom: 16px;
}
.hero .title { font-size: 20px; font-weight: 800; }
.hero .sub { font-size: 13px; opacity: 0.92; margin-top: 4px; }
.info-grid { display: flex; gap: 10px; margin-top: 6px; }
.info-box {
    flex: 1; background: #f7f7f9; border-radius: 14px;
    padding: 12px 8px; text-align: center;
}
.info-box .val { font-size: 20px; font-weight: 700; color: #222; }
.info-box .lbl { font-size: 11px; color: #888; }
.combo-item {
    background: #fff5f2;
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.combo-item .pair { font-weight: 700; color: #222; font-size: 15px; }
.combo-item .cnt {
    background: #ff6a88; color: white; border-radius: 20px;
    padding: 3px 12px; font-size: 12px; font-weight: 700;
}
.partner-item {
    background: #f2f7ff;
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

STAPLE_KEYWORDS = ["밥", "김치", "깍두기", "석박지"]


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
    return df


def clean_dish(item):
    item = item.strip()
    m = re.match(r"^(.*)\s\(([0-9.]+)\)$", item)
    return m.group(1).strip() if m else item


def parse_dish_set(ddish_nm):
    names = [clean_dish(x) for x in str(ddish_nm).split("<br/>") if x.strip()]
    return set(names)


def is_staple(name):
    return any(k in name for k in STAPLE_KEYWORDS)


df = load_data()

st.title("🍽️ 급식 메뉴 궁합 분석")

if df.empty:
    st.warning("불러올 수 있는 급식 데이터가 없습니다. meal.json 파일을 확인해 주세요.")
    st.stop()

schools = sorted(df["SCHUL_NM"].unique())
if len(schools) > 1:
    school = st.selectbox("🏫 학교 선택", schools)
    df = df[df["SCHUL_NM"] == school]
else:
    school = schools[0]

meal_types = sorted(df["MMEAL_SC_NM"].unique())
meal_options = ["전체"] + meal_types
meal_choice = st.radio("🍚 식사 종류", meal_options, horizontal=True)
if meal_choice != "전체":
    df = df[df["MMEAL_SC_NM"] == meal_choice]

col1, col2 = st.columns(2)
with col1:
    exclude_staple = st.checkbox("밥·김치류 제외하고 분석", value=True,
                                  help="매 끼니 거의 항상 나오는 주식/김치를 빼면 진짜 '조합'이 더 잘 보여요.")
with col2:
    min_count = st.slider("최소 등장 횟수", 2, 10, 3)

df = df.sort_values("날짜")
start_d = df["날짜"].min().strftime("%Y.%m.%d")
end_d = df["날짜"].max().strftime("%Y.%m.%d")

meal_dish_sets = []
for _, r in df.iterrows():
    dishes = parse_dish_set(r["DDISH_NM"])
    if exclude_staple:
        dishes = {d for d in dishes if not is_staple(d)}
    meal_dish_sets.append(dishes)

n_meals = len(meal_dish_sets)

single_counter = Counter()
pair_counter = Counter()
for dishes in meal_dish_sets:
    for d in dishes:
        single_counter[d] += 1
    for a, b in combinations(sorted(dishes), 2):
        pair_counter[(a, b)] += 1

st.markdown(f"""
<div class="hero">
    <div class="title">{school} · {meal_choice}</div>
    <div class="sub">{start_d} ~ {end_d} · 총 {n_meals}끼 데이터 분석</div>
</div>
""", unsafe_allow_html=True)

n_unique_dishes = len(single_counter)
n_combo_types = len([1 for v in pair_counter.values() if v >= min_count])

st.markdown(f"""
<div class="info-grid">
    <div class="info-box">
        <div class="val">{n_meals}</div>
        <div class="lbl">분석한 끼니 수</div>
    </div>
    <div class="info-box">
        <div class="val">{n_unique_dishes}</div>
        <div class="lbl">등장한 요리 가짓수</div>
    </div>
    <div class="info-box">
        <div class="val">{n_combo_types}</div>
        <div class="lbl">자주 등장한 조합 수</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("&nbsp;")
st.markdown("### 🥇 가장 자주 나온 메뉴 TOP 10")
top_singles = single_counter.most_common(10)
if top_singles:
    single_df = pd.DataFrame(top_singles, columns=["메뉴", "등장 횟수"]).set_index("메뉴")
    st.bar_chart(single_df, height=280)
else:
    st.info("조건에 맞는 메뉴가 없습니다.")

st.markdown("&nbsp;")
st.markdown("### 🍲 가장 자주 등장한 음식 조합")

valid_pairs = [(pair, cnt) for pair, cnt in pair_counter.items() if cnt >= min_count]
valid_pairs.sort(key=lambda x: x[1], reverse=True)

if not valid_pairs:
    st.info("조건에 맞는 조합이 없어요. 최소 등장 횟수를 낮춰보세요.")
else:
    top_pairs = valid_pairs[:15]
    for (a, b), cnt in top_pairs:
        st.markdown(f"""
        <div class="combo-item">
            <span class="pair">{a} + {b}</span>
            <span class="cnt">{cnt}번</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("&nbsp;")
    with st.expander("📊 연관성(리프트) 기준 '찰떡궁합' 조합 보기"):
        st.caption(
            "리프트(lift)는 두 메뉴가 우연히 함께 나올 확률보다 실제로 얼마나 더 자주 "
            "함께 나오는지를 나타내는 지표예요. 1보다 높을수록 '단짝' 조합입니다."
        )
        lift_rows = []
        for (a, b), cnt in valid_pairs:
            ca, cb = single_counter[a], single_counter[b]
            if ca == 0 or
