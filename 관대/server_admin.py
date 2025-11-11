# pages/server_admin.py
import streamlit as st
import pandas as pd
import plotly.express as px

def run():
    st.title("🖥 서버 운영 관리자")
    st.markdown("서버 상태, 트래픽, API 호출량을 실시간 모니터링합니다.")

    # 가상 데이터 예시
    traffic = pd.DataFrame({
        "hour": list(range(24)),
        "requests": [abs(1000 + 300 * ((h - 12) ** 2) / 50) for h in range(24)]
    })
    usage = pd.DataFrame({
        "hour": list(range(24)),
        "active_users": [int(50 + 40 * (h in range(18, 23))) for h in range(24)]
    })

    # --------------------------------------------------------
    # ⏰ 시간대별 앱 사용량
    # --------------------------------------------------------
    st.subheader("시간대별 앱 사용량")
    fig1 = px.line(usage, x="hour", y="active_users", title="시간대별 사용자 활동량", markers=True)
    st.plotly_chart(fig1, use_container_width=True)

    # --------------------------------------------------------
    # 🌐 API 요청 트래픽
    # --------------------------------------------------------
    st.subheader("API 요청 트래픽")
    fig2 = px.bar(traffic, x="hour", y="requests", title="시간대별 요청량")
    st.plotly_chart(fig2, use_container_width=True)

    # --------------------------------------------------------
    # 🧠 서버 상태 요약
    # --------------------------------------------------------
    st.metric(label="현재 활성 사용자", value="1,257명")
    st.metric(label="오늘 총 요청 수", value="56,241건")
    st.metric(label="평균 응답 시간", value="245 ms")
