import os
import streamlit as st
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from ics import Calendar, Event
from datetime import datetime, timedelta
import calendar

# -----------------------------
# .env 파일 불러오기
# -----------------------------
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

INDEX_NAME = "fooddata"

# -----------------------------
# 캐싱된 리소스 초기화
# -----------------------------
@st.cache_resource
def init_pinecone():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc.Index(INDEX_NAME)

@st.cache_resource
def get_vectorstore():
    index = init_pinecone()
    embedding = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )
    return PineconeVectorStore(index=index, embedding=embedding)

@st.cache_resource
def get_llm():
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.5,
        openai_api_key=OPENAI_API_KEY
    )

# -----------------------------
# Streamlit UI 기본 설정
# -----------------------------
st.set_page_config(
    page_title="건강 배터리 헬스케어",
    page_icon="🔋",
    layout="wide"
)

# CSS 적용
def apply_css():
    st.markdown("""
        <style>
            .main { background-color: #f4fff4; }
            h1, h2, h3 { color: #2e7d32; }
            section[data-testid="stSidebar"] { background-color: #e8f5e9; }
        </style>
    """, unsafe_allow_html=True)

apply_css()

st.title("💊 헬스케어 추천 서비스")

# -----------------------------
# 사이드바 메뉴
# -----------------------------
st.sidebar.image("건전지.png", width=120, caption="에너지 충전 중⚡")
menu = st.sidebar.radio("메뉴 선택", ["Main","회원가입", "추천", "식단 기록", "통계", "환경설정/내정보"])

# 구분선 후 환경설정
st.sidebar.markdown("<br><hr><br>", unsafe_allow_html=True)


# 빈 공간 넣기
for _ in range(20):
    st.sidebar.write("")

# -----------------------------
# Main 탭
# -----------------------------
if menu == "Main":
    st.subheader("메인 화면")

    if "current_date" not in st.session_state:
        st.session_state.current_date = datetime.today()
    if "show_full_calendar" not in st.session_state:
        st.session_state.show_full_calendar = False

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀", key="prev_week"):
            st.session_state.current_date -= timedelta(days=7)
    with col2:
        if st.button("📅 캘린더 전체보기", key="calendar_toggle"):
            st.session_state.show_full_calendar = not st.session_state.show_full_calendar
    with col3:
        if st.button("▶", key="next_week"):
            st.session_state.current_date += timedelta(days=7)

    if not st.session_state.show_full_calendar:
        today = st.session_state.current_date
        start_day = today - timedelta(days=3)
        days = [start_day + timedelta(days=i) for i in range(7)]

        st.write("### 이번 주")
        cols = st.columns(len(days))
        for i, d in enumerate(days):
            if d.date() == datetime.today().date():
                cols[i].markdown(f"**{d.day}**")
            else:
                cols[i].markdown(f"{d.day}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🍱 추천 식단")
            if "last_recommend" in st.session_state and st.session_state.last_recommend:
                st.info(st.session_state.last_recommend)
            else:
                st.write("여기에 추천 식단 표시")
        with col2:
            st.markdown("### ✍️ 식단 기록 입력")
            st.text_area("오늘 먹은 음식 기록하기")

    else:
        year = st.session_state.current_date.year
        month = st.session_state.current_date.month
        st.write(f"### {year}년 {month}월")
        cal = calendar.Calendar(firstweekday=6)
        weeks = cal.monthdayscalendar(year, month)
        for week in weeks:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].write(" ")
                elif (day == datetime.today().day 
                      and month == datetime.today().month 
                      and year == datetime.today().year):
                    cols[i].markdown(
                         f"""
                        <div style='
                            background:#4CAF50;
                            color:white;
                            font-weight:bold;
                            padding:5px;
                            border-radius:50%;
                            text-align:center;
                            font-size:16px;
                            display:inline-block;
                            min-width:28px;
                        '>{day}</div>
                    """,
                    unsafe_allow_html=True
                        
                    )
                else:
                    cols[i].write(day)

# -----------------------------
# 회원가입 탭
# -----------------------------
elif menu == "회원가입":
    st.subheader(" 회원가입")
    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")
    if st.button("회원가입 완료"):
        st.success(f"{username}님, 회원가입이 완료되었습니다!")

# -----------------------------
# 추천 탭
# -----------------------------
elif menu == "추천":
    st.subheader(" 맞춤형 추천 받기")
    query = st.text_area(
        "원하는 내용을 입력하세요",
        placeholder="예: 오늘 회식으로 삼겹살 먹었는데 내일 아침 뭐 먹으면 좋을까?"
    )

    col1, col2 = st.columns(2)
    with col1:
        recommend_btn = st.button("추천 받기")
    with col2:
        sync_btn = st.button("다음날 식단 추천")

    if recommend_btn:
        if query:
            try:
                docs = get_vectorstore().similarity_search(query, k=3)
                llm = get_llm()
                context = "\n".join([d.page_content for d in docs])
                response = llm.invoke(f"""
                사용자 요청: {query}
                참고 문서: {context}
                위 정보를 기반으로 건강/식단 추천을 해줘.
                """)

                st.session_state.last_recommend = response.content

                st.success("추천 결과")
                st.markdown(
                    f"""
                    <div style="padding:15px; background:#e8f5e9; border-radius:12px; margin:10px 0;">
                        <h4>오늘의 추천 식단 </h4>
                        <p>{response.content}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                c = Calendar()
                e = Event()
                e.name = "오늘의 추천 식단"
                e.begin = datetime.now()
                e.end = datetime.now() + timedelta(hours=1)
                e.description = response.content
                c.events.add(e)

                with open("recommendation.ics", "w", encoding="utf-8") as f:
                    f.writelines(str(c))

                st.download_button(
                    label=" iCalendar (.ics) 다운로드",
                    data=str(c),
                    file_name="recommendation.ics",
                    mime="text/calendar"
                )

            except Exception as e:
                st.error(f"에러 발생: {str(e)}")
        else:
            st.warning("먼저 내용을 입력해주세요!")

    if sync_btn:
        try:
            with open("recommendation.ics", "r", encoding="utf-8") as f:
                c = Calendar(f.read())
            last_event = list(c.events)[-1]
            last_meal = last_event.description
            llm = get_llm()
            response = llm.invoke(f"""
            이전 식단 기록: {last_meal}
            위 식단을 고려하여, 내일 먹으면 좋은 식단을 추천해줘.
            """)
            st.success("다음 식단 추천 결과")
            st.write(response.content)
        except FileNotFoundError:
            st.warning("저장된 식단 일정(ICS 파일)이 없습니다. 먼저 추천을 받아주세요.")

# -----------------------------
# 식단 기록 탭
# -----------------------------
elif menu == "식단 기록":
    st.subheader(" 식단 기록")
    st.write("사용자가 먹은 음식을 기록하는 페이지")

# -----------------------------
# 통계 탭
# -----------------------------
elif menu == "통계":
    st.subheader(" 통계")
    col1, col2, col3 = st.columns(3)
    
    box_style = """
        background:#f5f5f5;
        padding:10px;
        border-radius:8px;
        text-align:center;
        min-height:80px;       /* 높이 고정 */
        display:flex;
        flex-direction:column;
        justify-content:center; /* 세로 가운데 정렬 */
    """
    
    st.markdown("""
    <div style="display:flex; gap:10px;">
        <div style="flex:1; background:#f5f5f5; min-height:80px; 
                    border-radius:8px; text-align:center; padding:10px;">
            <b>일간<br>총 칼로리 량<br>(고정)</b>
        </div>
        <div style="flex:1; background:#f5f5f5; min-height:80px; 
                    border-radius:8px; text-align:center; padding:10px;">
            <b>주간<br>총 칼로리 량<br>(고정)</b>
        </div>
        <div style="flex:1; background:#f5f5f5; min-height:80px; 
                    border-radius:8px; text-align:center; padding:10px;">
            <b>추후 추가 예정<br>(고정)</b>
        </div>
    </div>
    """, unsafe_allow_html=True)


    st.markdown("---")

    # -----------------------------
    # 탭 (일간 / 주간 / 월간)
    # -----------------------------
    tab1, tab2, tab3 = st.tabs(["일간", "주간", "월간"])

    with tab1:
        st.info("📅 일간 그래프 자리")
        st.write("일간 데이터 기반 그래프를 여기에 표시")

    with tab2:
        st.info("📅 주간 그래프 자리")
        st.write("주간 데이터 기반 그래프를 여기에 표시")

    with tab3:
        st.info("📅 월간 그래프 자리")
        st.write("월간 데이터 기반 그래프를 여기에 표시")
        
elif menu == "환경설정/내정보":
    st.subheader("⚙️ 환경설정 / 내정보")
    st.markdown("""
    <div style="text-align:left; font-size:16px; line-height:2;">
        <p>닉네임 변경</p>
        <p>비밀번호 변경</p>
        <p>내 정보 변경 (키, 체중, 목표 바꾸기)</p>
        <p>다크모드 / 화이트모드</p>
    </div>
    """, unsafe_allow_html=True)

   
