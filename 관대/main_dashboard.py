import streamlit as st
import data_admin
import server_admin

st.set_page_config(page_title="Cookus 관리자 대시보드", layout="wide")

st.sidebar.title("👑 관리자 대시보드")
tab = st.sidebar.radio("관리자 역할 선택", ["데이터 수집·보완 관리자", "서버 운영 관리자"])

if tab == "데이터 수집·보완 관리자":
    data_admin.run()
elif tab == "서버 운영 관리자":
    server_admin.run()
