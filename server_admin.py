# server_admin.py
import pandas as pd
import streamlit as st
import plotly.express as px
from db import get_conn, T   # data_admin과 동일한 공용 연결

# ---------- 공통 유틸 ----------
def qdf(sql: str, params=None) -> pd.DataFrame:
    """쿼리 → cursor.fetchall() → DataFrame (DictCursor 기준)"""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall()
        return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"집계 실패: {e}")
        return pd.DataFrame()

def qscalar(sql: str, params=None, default: int = 0) -> int:
    df = qdf(sql, params)
    if df.empty:
        return default
    val = list(df.iloc[0].values)[0]
    return int(pd.to_numeric(pd.Series([val]), errors="coerce").fillna(default).iloc[0])

def to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)

def drop_header_row_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    """첫 행이 컬럼명과 동일하면(헤더가 데이터로 들어온 경우) 제거"""
    if df.empty:
        return df
    first = df.iloc[0].astype(str).str.strip().str.lower().tolist()
    cols  = [c.strip().lower() for c in df.columns.tolist()]
    if first == cols:
        return df.iloc[1:].reset_index(drop=True)
    return df

def rename_ko(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """존재하는 컬럼만 안전하게 한글로 리네임"""
    if df.empty:
        return df
    safe = {k: v for k, v in mapping.items() if k in df.columns}
    return df.rename(columns=safe)

# ---------- 페이지 ----------
def run():
    st.title("🖥 서버 운영 관리자")
    st.markdown("서버 상태와 커뮤니티 활동을 요약해 보여줍니다. (기존 테이블만 사용)")

    # ===== 상단 KPI =====
    active_users_10m = qscalar(f"""
        SELECT COUNT(DISTINCT user_id) AS cnt
        FROM {T('user_refresh_token')}
        WHERE revoked = 0
          AND created_at >= NOW() - INTERVAL 10 MINUTE
    """, default=0)

    total_posts = qscalar(f"SELECT COUNT(*) AS cnt FROM {T('board')}", default=0)

    total_likes_7d = qscalar(f"""
        SELECT COUNT(*) AS cnt
        FROM {T('board_likes')}
        WHERE created_at >= NOW() - INTERVAL 7 DAY
    """, default=0)

    today_posts = qscalar(f"""
        SELECT COUNT(*) AS cnt
        FROM {T('board')}
        WHERE DATE(created_at) = CURDATE()
    """, default=0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재 활성 사용자(10분)", f"{active_users_10m}명")
    c2.metric("총 게시글", f"{total_posts}개")
    c3.metric("최근 7일 좋아요", f"{total_likes_7d}건")
    c4.metric("오늘 신규 게시글", f"{today_posts}개")

    st.divider()

    # ===== 시간대별 앱 사용량(오늘) =====
    st.subheader("시간대별 앱 사용량 (오늘, 최근 활동 기준)")

    usage = qdf(f"""
        SELECT HOUR(created_at) AS hour, COUNT(DISTINCT user_id) AS active_users
        FROM {T('user_refresh_token')}
        WHERE DATE(created_at) = CURDATE()
        GROUP BY HOUR(created_at)
        ORDER BY hour
    """)
    usage = drop_header_row_if_needed(usage)

    full_hours = pd.DataFrame({"hour": list(range(24))})
    if not usage.empty:
        usage["hour"] = to_int(usage["hour"])
        usage["active_users"] = to_int(usage["active_users"])
        usage = full_hours.merge(usage, on="hour", how="left")
        usage["active_users"] = to_int(usage["active_users"])
    else:
        usage = full_hours.assign(active_users=0)

    fig_usage = px.line(
        usage, x="hour", y="active_users", markers=True,
        title="시간대별 활성 사용자 수",
        labels={"hour": "시간(시)", "active_users": "활성 사용자 수"}
    )
    st.plotly_chart(fig_usage, width='stretch')

    # ===== 최근 7일간 앱 사용량 (일별 고유 로그인 수) =====
    st.subheader("최근 7일간 앱 사용량 (일별 고유 로그인 수)")

    daily7 = qdf(f"""
        SELECT DATE(created_at) AS d, COUNT(DISTINCT user_id) AS users
        FROM {T('user_refresh_token')}
        WHERE DATE(created_at) >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(created_at)
        ORDER BY d
    """)
    daily7 = drop_header_row_if_needed(daily7)

    today = pd.to_datetime(pd.Timestamp.today().date())
    date_frame = pd.DataFrame({"d": pd.date_range(end=today, periods=7, freq="D").date})

    if not daily7.empty:
        daily7["d"] = pd.to_datetime(daily7["d"]).dt.date
        daily7["users"] = to_int(daily7["users"])
        daily7 = date_frame.merge(daily7, on="d", how="left")
        daily7["users"] = to_int(daily7["users"])
    else:
        daily7 = date_frame.assign(users=0)

    fig_daily7 = px.bar(
        daily7, x="d", y="users", text="users",
        title="최근 7일 일자별 로그인 사용자 수",
        labels={"d": "날짜", "users": "로그인 사용자 수"}
    )
    fig_daily7.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig_daily7, width='stretch')
    st.caption("※ ‘오늘’ 값은 집계가 진행 중인 값이에요.")

    st.divider()

    # ===== 커뮤니티 활동 요약 =====
    st.subheader("커뮤니티 활동 요약")

    # 오늘 작성된 게시글 (표시 개수 조절)
    limit_n = st.slider("오늘 글 표시 개수", min_value=5, max_value=50, value=10, step=5)
    today_list = qdf(f"""
        SELECT content_id, user_id, content_title, like_count, created_at
        FROM {T('board')}
        WHERE DATE(created_at) = CURDATE()
        ORDER BY created_at DESC
        LIMIT {limit_n}
    """)
    today_list = drop_header_row_if_needed(today_list)
    if today_list.empty:
        st.info("오늘 작성된 게시글이 없어요.")
    else:
        today_list["like_count"] = to_int(today_list["like_count"])
        today_list = rename_ko(
            today_list,
            {
                "content_id": "게시글ID",
                "user_id": "작성자ID",
                "content_title": "제목",
                "like_count": "좋아요",
                "created_at": "작성일"
            }
        )
        st.dataframe(today_list, width='stretch')

    # 최근 7일 좋아요(일자별)
    likes_daily = qdf(f"""
        SELECT DATE(created_at) AS d, COUNT(*) AS likes
        FROM {T('board_likes')}
        WHERE created_at >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(created_at)
        ORDER BY d
    """)
    likes_daily = drop_header_row_if_needed(likes_daily)

    base_dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=7).date
    base_df = pd.DataFrame({"d": base_dates})

    if not likes_daily.empty:
        likes_daily["d"] = pd.to_datetime(likes_daily["d"]).dt.date
        likes_daily = base_df.merge(likes_daily, on="d", how="left")
        likes_daily["likes"] = to_int(likes_daily["likes"])
    else:
        likes_daily = base_df.assign(likes=0)

    fig_likes = px.bar(
        likes_daily, x="d", y="likes",
        title="최근 7일 일자별 좋아요 수",
        labels={"d": "날짜", "likes": "좋아요 수"}
    )
    st.plotly_chart(fig_likes, width='stretch')

    st.divider()

    # ===== 인기 게시글 Top 10 =====
    st.subheader("인기 게시글 Top 10 (최근 7일, 좋아요 순)")
    top_posts = qdf(f"""
        SELECT content_id, user_id, content_title, like_count, created_at
        FROM {T('board')}
        WHERE created_at >= NOW() - INTERVAL 7 DAY
        ORDER BY like_count DESC, created_at DESC
        LIMIT 10
    """)
    top_posts = drop_header_row_if_needed(top_posts)

    if top_posts.empty:
        st.info("최근 7일 내 인기 게시글이 없어요.")
    else:
        if "like_count" in top_posts.columns:
            top_posts["like_count"] = to_int(top_posts["like_count"])
        # 순위 추가 → 표 한글 컬럼으로 리네임
        top_posts = top_posts.reset_index(drop=True)
        top_posts.insert(0, "순위", range(1, len(top_posts) + 1))
        top_posts = rename_ko(
            top_posts,
            {
                "content_id": "게시글ID",
                "user_id": "작성자ID",
                "content_title": "제목",
                "like_count": "좋아요",
                "created_at": "작성일"
            }
        )
        top_posts = top_posts.set_index("순위")
        st.dataframe(top_posts, width='stretch')

    st.divider()

    # ===== 진행 중인 대회 & 출품작 =====
    st.subheader("대회 현황")

    # 진행 중 대회 + 게시물 수
    ongoing = qdf(f"""
        SELECT e.event_id, e.event_name, e.start_date, e.end_date, COALESCE(COUNT(b.content_id), 0) AS post_count
        FROM {T('event')} e
        LEFT JOIN {T('board')} b ON b.event_id = e.event_id
        WHERE CURDATE() BETWEEN e.start_date AND e.end_date
        GROUP BY e.event_id, e.event_name, e.start_date, e.end_date
        ORDER BY e.start_date
    """)
    ongoing = drop_header_row_if_needed(ongoing)
    if not ongoing.empty:
        ongoing["post_count"] = to_int(ongoing["post_count"])
        ongoing = rename_ko(
            ongoing,
            {
                "event_id": "대회ID",
                "event_name": "대회명",
                "start_date": "시작일",
                "end_date": "종료일",
                "post_count": "게시물 수"
            }
        )

    # 종료된 대회 + 게시물 수
    finished = qdf(f"""
        SELECT e.event_id, e.event_name, e.start_date, e.end_date, COALESCE(COUNT(b.content_id), 0) AS post_count
        FROM {T('event')} e
        LEFT JOIN {T('board')} b ON b.event_id = e.event_id
        WHERE e.end_date < CURDATE()
        GROUP BY e.event_id, e.event_name, e.start_date, e.end_date
        ORDER BY e.end_date DESC
    """)
    finished = drop_header_row_if_needed(finished)
    if not finished.empty:
        finished["post_count"] = to_int(finished["post_count"])
        finished = rename_ko(
            finished,
            {
                "event_id": "대회ID",
                "event_name": "대회명",
                "start_date": "시작일",
                "end_date": "종료일",
                "post_count": "게시물 수"
            }
        )

    # 요약 KPI
    c1, c2 = st.columns(2)
    c1.metric("진행 중 대회 수", f"{0 if ongoing.empty else len(ongoing)}개")
    c2.metric("종료된 대회 수", f"{0 if finished.empty else len(finished)}개")
    st.divider()

    # 진행 중 대회 표 (인덱스 숨김)
    st.markdown("### 🟢 진행 중 대회")
    if ongoing.empty:
        st.info("진행 중인 대회가 없어요.")
    else:
        st.dataframe(
            ongoing.reset_index(drop=True)[["대회ID", "대회명", "시작일", "종료일", "게시물 수"]],
            width='stretch'
        )

    # 종료된 대회 표
    st.markdown("### ⚪ 종료된 대회")
    if finished.empty:
        st.info("종료된 대회가 없어요.")
    else:
        st.dataframe(
            finished.reset_index(drop=True)[["대회ID", "대회명", "시작일", "종료일", "게시물 수"]],
            width='stretch'
        )

if __name__ == "__main__":
    run()
