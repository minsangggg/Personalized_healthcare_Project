import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_conn

def run():
    st.title("📊 데이터 수집·보완 관리자")
    st.markdown("Cookus 플랫폼의 사용자 행동과 추천 데이터를 분석합니다.")

    conn = get_conn()

    # === 1️⃣ 기본 데이터 로드 ===
    df_user = pd.read_sql("SELECT * FROM user_info WHERE is_deleted = 0", conn)
    df_fridge = pd.read_sql("SELECT * FROM fridge_item", conn)
    df_recipe = pd.read_sql("SELECT * FROM recipe", conn)
    df_rec_rec = pd.read_sql("SELECT * FROM recommend_recipe", conn)
    df_sel = pd.read_sql("SELECT * FROM selected_recipe", conn)

    # === 2️⃣ 사용자 통계 ===
    st.subheader("👥 사용자 구성 비율")
    gender_count = df_user["gender"].value_counts().reset_index()
    gender_count.columns = ["gender", "count"]  # 컬럼명 명시적으로 설정
    fig1 = px.pie(gender_count, names="gender", values="count", title="성별 분포")
    st.plotly_chart(fig1, use_container_width=True)

    level_count = df_user["cooking_level"].value_counts().reset_index()
    level_count.columns = ["cooking_level", "count"]  # 컬럼명 재정의
    fig2 = px.bar(level_count, x="cooking_level", y="count",
              title="요리 수준 분포 (상/하)", text_auto=True)
    st.plotly_chart(fig2, use_container_width=True)

    # --------------------------------------------------
    # 3️⃣ 냉장고 데이터
    # --------------------------------------------------
    st.header("🧊 냉장고 재료 데이터")

    top_ing = df_fridge["ingredient_name"].value_counts().head(10).reset_index()
    top_ing.columns = ["ingredient_name", "count"]
    fig3 = px.bar(top_ing, x="ingredient_name", y="count",
                title="사용자들이 가장 많이 보유한 재료 TOP 10",
                text_auto=True, color_discrete_sequence=["#A3C9A8"])
    st.plotly_chart(fig3, use_container_width=True)

    avg_q = df_fridge.groupby("ingredient_name")["quantity"].mean().reset_index()
    fig4 = px.bar(avg_q.sort_values("quantity", ascending=False).head(10),
                x="ingredient_name", y="quantity",
                title="재료별 평균 보유량", text_auto=True)
    st.plotly_chart(fig4, use_container_width=True)


    # === 4️⃣ 추천 → 선택 전환율 ===
    st.subheader("🍳 추천 레시피 전환율")
    total_recs = len(df_rec_rec)
    total_selected = len(df_sel)
    conversion_rate = (total_selected / total_recs * 100) if total_recs > 0 else 0
    st.metric(label="추천 → 실제 요리 실행 전환율", value=f"{conversion_rate:.2f}%")

    # 추천/선택 날짜별 추이
    rec_trend = df_rec_rec["recommend_dt"].dt.date.value_counts().sort_index()
    sel_trend = df_sel["selected_date"].dt.date.value_counts().sort_index()
    df_trend = pd.DataFrame({"추천": rec_trend, "선택": sel_trend}).fillna(0)
    fig5 = px.line(df_trend, title="추천 vs 실제 선택 추이 (일별)")
    st.plotly_chart(fig5, use_container_width=True)

    # === 5️⃣ 인기 레시피 ===
    st.subheader("🔥 인기 레시피 TOP 5")
    popular_recipes = df_sel["recipe_id"].value_counts().head(5).reset_index()
    popular_recipes = popular_recipes.merge(df_recipe, left_on="index", right_on="recipe_id", how="left")
    st.dataframe(popular_recipes[["recipe_nm_ko", "cooking_time", "level_nm", "servings"]])

    fig6 = px.bar(popular_recipes, x="recipe_nm_ko", y="recipe_id",
                  title="가장 많이 선택된 레시피 TOP 5")
    st.plotly_chart(fig6, use_container_width=True)

    # === 6️⃣ 요리 난이도별 평균 조리시간 ===
    st.subheader("⏱ 난이도별 평균 조리시간")
    level_time = df_recipe.groupby("level_nm")["cooking_time"].mean().reset_index()
    fig7 = px.bar(level_time, x="level_nm", y="cooking_time", title="난이도별 평균 조리시간 (분)")
    st.plotly_chart(fig7, use_container_width=True)

    # === 7️⃣ 상/하 요리레벨별 행동 패턴 ===
    st.subheader("📈 요리 수준별 선택 패턴 비교")
    df_merge = df_sel.merge(df_user, on="id", how="left").merge(df_recipe, on="recipe_id", how="left")
    level_pref = df_merge.groupby(["cooking_level", "ty_nm"]).size().reset_index(name="count")
    fig8 = px.bar(level_pref, x="ty_nm", y="count", color="cooking_level",
                  barmode="group", title="요리 수준별 선호 요리 유형")
    st.plotly_chart(fig8, use_container_width=True)

    conn.close()
