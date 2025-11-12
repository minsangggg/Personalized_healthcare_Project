# data_admin.py
import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_conn  # 공용 DB 연결

# 메인에서 set_page_config를 이미 호출하므로 여기선 호출하지 않음

def run():
    st.title("👥 사용자 통계 대시보드")
    st.markdown("DB의 `user_info` 테이블 기반 통계 시각화")

    # --- 데이터 로드 ---
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_info")
                rows = cur.fetchall()
        df_user = pd.DataFrame(rows)

        if df_user.empty:
            st.warning("⚠️ user_info 테이블에 데이터가 없습니다.")
        else:
            st.success(f"✅ {len(df_user)}명 사용자 데이터 로드 완료!")

    except Exception as e:
        st.error(f"❌ DB 연결 실패: {e}")
        st.stop()

    # --- 데이터 컬럼 확인 ---
    st.write("### 🔍 컬럼 미리보기")
    st.dataframe(df_user.head(), use_container_width=True)  # Streamlit 경고 뜨면 width='stretch'로 바꿔도 OK

    # --- 성별 분포 ---
    if "gender" in df_user.columns:
        st.subheader("👩‍🦰 성별 비율")
        gender_count = df_user["gender"].value_counts().reset_index()
        gender_count.columns = ["gender", "count"]
        fig1 = px.pie(
            gender_count,
            names="gender",
            values="count",
            title="성별 비율",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("⚠️ 'gender' 컬럼이 존재하지 않습니다.")

    # --- 연령대 비율 ---
    if "age" in df_user.columns:
        st.subheader("🎂 연령대 비율")
        df_user["age_group"] = pd.cut(
            df_user["age"],
            bins=[0, 19, 29, 39, 49, 59, 69, 120],
            labels=["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대 이상"]
        )
        age_count = df_user["age_group"].value_counts().sort_index().reset_index()
        age_count.columns = ["age_group", "count"]
        fig2 = px.bar(
            age_count,
            x="age_group",
            y="count",
            title="연령대별 사용자 분포",
            text_auto=True
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("⚠️ 'age' 컬럼이 존재하지 않습니다.")

    # --- 요리 수준 비율 ---
    if "cooking_level" in df_user.columns:
        st.subheader("🍳 요리 수준 비율")
        level_count = df_user["cooking_level"].value_counts().reset_index()
        level_count.columns = ["cooking_level", "count"]
        fig3 = px.bar(
            level_count,
            x="cooking_level",
            y="count",
            title="요리 수준 분포 (상/하)",
            text_auto=True
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("⚠️ 'cooking_level' 컬럼이 존재하지 않습니다.")

    # --- 요약 통계 ---
    st.markdown("### 📊 요약 통계")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 사용자 수", len(df_user))
    if "gender" in df_user.columns:
        col2.metric("여성 비율", f"{(df_user['gender'].eq('female').mean() * 100):.1f}%")
    if "cooking_level" in df_user.columns and not df_user["cooking_level"].empty:
        top_level = df_user["cooking_level"].value_counts().idxmax()
        col3.metric("가장 많은 요리 수준", top_level)

    st.info("✅ 사용자 통계 대시보드 로드 완료")
