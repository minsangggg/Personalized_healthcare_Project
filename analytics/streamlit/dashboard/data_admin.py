import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from db import get_conn


THEME_COLORS = {
    "cream": "#FFE7B8",
    "orange": "#F5B14C",
    "brown": "#A5672B",
    "beige": "#FFF6E5",
    "black": "#000000",
}

COLOR_SEQUENCE = [
    THEME_COLORS["orange"],
    THEME_COLORS["brown"],
    THEME_COLORS["cream"],
    THEME_COLORS["beige"],
]
px.defaults.color_discrete_sequence = COLOR_SEQUENCE


def apply_theme(fig):
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=THEME_COLORS["brown"]),
        legend=dict(bgcolor="rgba(255,255,255,0)"),
    )
    return fig


def run():
    st.title("📊 사용자 인사이트 대시보드")

    def to_age_group(dob: pd.Series) -> pd.Categorical:
        today = pd.to_datetime(date.today())
        age = (today - pd.to_datetime(dob, errors="coerce")).dt.days // 365
        bins = [-1, 19, 29, 39, 49, 59, 69, 200]
        labels = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대 이상"]
        return pd.cut(age, bins=bins, labels=labels)

    @st.cache_data(show_spinner=False)
    def load_user_info():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, gender, date_of_birth, cooking_level
            FROM user_info
        """
        )
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows)

    @st.cache_data(show_spinner=False)
    def load_fridge_item():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ingredient_name
            FROM fridge_item
        """
        )
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows)

    @st.cache_data(show_spinner=False)
    def load_selected_recipe():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT selected_id, id AS uid, recipe_id, action
            FROM selected_recipe
            WHERE recipe_id IS NOT NULL
        """
        )
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows)

    @st.cache_data(show_spinner=False)
    def load_recipe():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT recipe_id, ty_nm
            FROM recipe
        """
        )
        rows = cur.fetchall()
        conn.close()
        return pd.DataFrame(rows)

    with st.spinner("데이터 불러오는 중..."):
        df_user = load_user_info()
        df_fridge = load_fridge_item()
        df_sel = load_selected_recipe()
        df_recipe = load_recipe()

    if not df_user.empty:
        df_user["gender"] = (
            df_user["gender"].astype(str).str.strip().str.lower().replace({"female": "female", "male": "male"})
        )
        df_user = df_user[df_user["gender"].isin(["female", "male"])]
        df_user["age_group"] = to_age_group(df_user["date_of_birth"])
        df_user = df_user.dropna(subset=["age_group"])
        df_user["cooking_level"] = df_user["cooking_level"].astype(str).str.strip()
        df_user = df_user[df_user["cooking_level"].isin(["상", "하"])]

    st.markdown("---")
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        st.markdown("#### ① 연령대별·성별 요리 난이도 분포")
        if not df_user.empty:
            grp = df_user.groupby(["age_group", "gender", "cooking_level"]).size().reset_index(name="cnt")

            male_df = grp[grp["gender"] == "male"]
            female_df = grp[grp["gender"] == "female"]

            fig1 = go.Figure()

            female_colors = {"상": THEME_COLORS["orange"], "하": THEME_COLORS["cream"]}
            male_colors = {"상": THEME_COLORS["brown"], "하": THEME_COLORS["beige"]}

            for lvl in ["상", "하"]:
                sub = female_df[female_df["cooking_level"] == lvl]
                fig1.add_trace(
                    go.Bar(
                        x=sub["age_group"],
                        y=sub["cnt"],
                        name=f"여성-{lvl}",
                        marker_color=female_colors[lvl],
                        offsetgroup="female",
                    )
                )

            for lvl in ["상", "하"]:
                sub = male_df[male_df["cooking_level"] == lvl]
                fig1.add_trace(
                    go.Bar(
                        x=sub["age_group"],
                        y=sub["cnt"],
                        name=f"남성-{lvl}",
                        marker_color=male_colors[lvl],
                        offsetgroup="male",
                    )
                )

            fig1.update_layout(
                barmode="stack",
                height=400,
                bargap=0.2,
                title="연령대별·성별 요리 수준 분포 (개수 기준)",
                xaxis=dict(
                    title="연령대",
                    categoryorder="array",
                    categoryarray=["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대 이상"],
                ),
                yaxis_title="인원 수",
                legend_title_text="성별-요리수준",
                font=dict(size=11),
                margin=dict(t=40, b=40, l=30, r=30),
            )
            apply_theme(fig1)
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning("데이터 없음")

    with col2:
        st.markdown("#### ② 연령대별·성별 Top3 보유 재료")
        if not df_fridge.empty and not df_user.empty:
            df_fr = df_fridge.rename(columns={"id": "uid"})
            df_u = df_user.rename(columns={"id": "uid"})[["uid", "age_group", "gender"]]
            merged = df_fr.merge(df_u, on="uid", how="inner")
            merged["ingredient_name"] = merged["ingredient_name"].astype(str).str.strip()

            age_options = sorted(merged["age_group"].dropna().unique(), key=lambda x: str(x))
            sel_age = st.selectbox("연령대를 선택하세요", age_options, key="age_selector")

            sub = merged[merged["age_group"] == sel_age]
            if not sub.empty:
                top_by_gender = sub.groupby(["gender", "ingredient_name"]).size().reset_index(name="cnt")

                def top3(df_g):
                    return df_g.sort_values("cnt", ascending=False).head(3)

                topF = top3(top_by_gender[top_by_gender["gender"] == "female"])
                topM = top3(top_by_gender[top_by_gender["gender"] == "male"])
                top_all = pd.concat([topF, topM], ignore_index=True)

                fig2 = px.bar(
                    top_all,
                    x="ingredient_name",
                    y="cnt",
                    color="gender",
                    barmode="group",
                    text_auto=True,
                    labels={"ingredient_name": "재료명", "cnt": "보유 수(건)"},
                    title=f"{sel_age} - 성별 Top3 보유 재료",
                    color_discrete_map={
                        "female": THEME_COLORS["orange"],
                        "male": THEME_COLORS["cream"],
                    },
                )
                apply_theme(fig2)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("선택한 연령대 데이터가 없습니다.")
        else:
            st.warning("데이터 없음")

    with col3:
        st.markdown("#### ③ 전체 유저의 추천 → 실제 요리 전환율")
        if not df_sel.empty and "action" in df_sel.columns:
            total = len(df_sel)
            converted = int((df_sel["action"] == 1).sum())
            rate = (converted / total * 100) if total > 0 else 0.0

            m1, m2, m3 = st.columns(3)
            m1.metric("전체 로그", f"{total:,}")
            m2.metric("실제 요리(=1)", f"{converted:,}")
            m3.metric("전환율", f"{rate:.1f}%")

            df_conv = pd.DataFrame(
                {
                    "label": ["추천 후 조리완료", "추천 후 미조리"],
                    "value": [converted, total - converted],
                }
            )
            fig3 = px.pie(
                df_conv,
                names="label",
                values="value",
                title="전체 전환율 (Donut)",
                hole=0.4,
                color="label",
                color_discrete_map={
                    "추천 후 조리완료": THEME_COLORS["orange"],
                    "추천 후 미조리": THEME_COLORS["cream"],
                },
            )
            fig3.update_traces(
                textposition="inside",
                textinfo="percent",
                textfont_size=20,
                textfont_weight="bold",
                insidetextorientation="horizontal",
            )
            apply_theme(fig3)
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown("#### ④ 레벨별 레시피 유형 선택 패턴")
        if not df_sel.empty and not df_recipe.empty and not df_user.empty:
            df_sel1 = df_sel[df_sel["action"] == 1].copy()
            j1 = df_sel1.merge(df_recipe, on="recipe_id", how="left")
            df_u = df_user.rename(columns={"id": "uid"})[["uid", "cooking_level"]]
            j2 = j1.merge(df_u, on="uid", how="left")
            j2 = j2.dropna(subset=["ty_nm", "cooking_level"])
            j2 = j2[j2["cooking_level"].isin(["상", "하"])]

            ty_lv = (
                j2.groupby(["ty_nm", "cooking_level"])
                .size()
                .reset_index(name="cnt")
                .sort_values("cnt", ascending=False)
            )

            N = st.slider("시각화할 유형 상위 N", 5, 25, 12, 1, key="ty_slider")
            topN_types = ty_lv.groupby("ty_nm")["cnt"].sum().nlargest(N).index.tolist()
            vis = ty_lv[ty_lv["ty_nm"].isin(topN_types)]

            fig4 = px.bar(
                vis,
                x="ty_nm",
                y="cnt",
                color="cooking_level",
                barmode="group",
                text_auto=True,
                labels={"ty_nm": "레시피 유형", "cnt": "선택 수(액션=1)"},
                title=f"레벨별 레시피 유형 선택 비교 (상위 {N} 유형)",
                color_discrete_map={
                    "상": THEME_COLORS["brown"],
                    "하": THEME_COLORS["orange"],
                },
            )
            apply_theme(fig4)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("데이터 없음")
