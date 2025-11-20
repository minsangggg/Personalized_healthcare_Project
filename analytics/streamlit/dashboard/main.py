import streamlit as st

st.set_page_config(page_title="Cookus 관리자 대시보드", layout="wide")

import data_admin
import server_admin
import user_dashboard
from login import ensure_login, SESSION_ROLE_KEY, SESSION_USER_KEY

if not ensure_login():
    st.stop()

user_role = st.session_state.get(SESSION_ROLE_KEY)
user_id = st.session_state.get(SESSION_USER_KEY)

if user_role == "admin":
    st.sidebar.title("관리자 대시보드")
    tab = st.sidebar.radio("관리자 역할 선택", ["데이터 수집·보완 관리자", "서버 운영 관리자"])

    if tab == "데이터 수집·보완 관리자":
        data_admin.run()
    elif tab == "서버 운영 관리자":
        server_admin.run()
elif user_role == "user":
    st.sidebar.title("나의 대시보드")

    if user_id:
        user_dashboard.run(user_id)
    else:
        st.error("사용자 정보를 불러올 수 없습니다. 다시 로그인해 주세요.")
else:
    st.warning("로그인 세션에 오류가 발생했습니다. 로그아웃 후 다시 시도해 주세요.")
