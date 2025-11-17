from __future__ import annotations

import datetime as dt
from typing import Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from db_client import DatabaseNotConfigured, healthcheck
from queries import (
    get_age_group_top_ingredients,
    get_age_level_and_time_stats,
    get_hourly_app_usage,
    get_ingredient_trend,
    get_top_ingredients_overall,
)


st.set_page_config(page_title="CookUS Insights", layout="wide")

st.markdown(
    """
    <style>
section[data-testid="stSidebar"] {
        padding-left: 5px !important;
        padding-right: 12px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stDateInput"] {
        min-width: 280px;
    }

    section[data-testid="stSidebar"] div[data-testid="stDateInput"] .stDateInput {
        position: relative;
    }

    section[data-testid="stSidebar"] div[data-testid="stDateInput"] .stDateInput > div:last-child {
        margin-left: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("CookUS Insight Dashboard")
st.caption("MariaDB 데이터를 기반으로 연령·재료·사용 패턴을 파악합니다.")


def _normalize_date_input(
    date_input_value,
) -> Tuple[Optional[str], Optional[str]]:
    if isinstance(date_input_value, tuple) and len(date_input_value) == 2:
        start, end = date_input_value
    else:
        start = end = date_input_value

    def _to_str(value):
        return value.isoformat() if isinstance(value, dt.date) else None

    return _to_str(start), _to_str(end)


def _ensure_pandas(df):
    """Streamlit cache may return Narwhals DataFrame; convert to pandas when needed."""
    if hasattr(df, "to_pandas"):
        try:
            return df.to_pandas()
        except Exception:
            pass
    return df


with st.sidebar:
    st.header("필터")
    today = dt.date.today()
    default_range = (today - dt.timedelta(days=30), today)

    selected_range = st.date_input("추천/선택 기준 기간", value=default_range)
    start_date, end_date = _normalize_date_input(selected_range)

    top_n = st.slider("연령대별 재료 TOP N", min_value=3, max_value=5, value=3, step=1)
    trend_window = st.selectbox(
        "재료 트렌드 단위",
        options=[("day", "일간"), ("week", "주간"), ("month", "월간")],
        format_func=lambda x: x[1],
    )[0]

    st.divider()
    st.markdown("**DB 상태**")
    try:
        db_status = healthcheck()
        if db_status["ok"]:
            st.success("연결 정상")
        else:
            st.error(db_status["message"])
    except DatabaseNotConfigured as exc:
        st.warning(str(exc))
        st.stop()


@st.cache_data(ttl=600)
def load_age_level_data(start: Optional[str], end: Optional[str]):
    return get_age_level_and_time_stats(start, end)


@st.cache_data(ttl=600)
def load_age_group_ingredients(top_k: int):
    return get_age_group_top_ingredients(top_k)


@st.cache_data(ttl=600)
def load_hourly_usage(start: Optional[str], end: Optional[str]):
    return get_hourly_app_usage(start, end)


@st.cache_data(ttl=600)
def load_overall_ingredients(limit: int = 15):
    return get_top_ingredients_overall(limit)


@st.cache_data(ttl=600)
def load_ingredient_trend(keyword: str, window: str):
    return get_ingredient_trend(keyword, window)


age_tab, ingredient_tab, usage_tab = st.tabs(
    ["연령대·난이도", "재료 인사이트", "사용량/트렌드"]
)

with age_tab:
    st.subheader("연령대별 요리 난이도 & 조리시간 분포")
    age_data = load_age_level_data(start_date, end_date)
    level_df = _ensure_pandas(age_data["level_summary"])
    time_df = _ensure_pandas(age_data["time_distribution"])

    if level_df.empty:
        st.info("표시할 추천 데이터가 없습니다.")
    else:
        level_chart = (
            alt.Chart(level_df)
            .mark_bar()
            .encode(
                x=alt.X("age_group:N", title="연령대"),
                y=alt.Y("recommendation_count:Q", title="추천 수"),
                color=alt.Color("cooking_level:N", title="요리 난이도"),
                tooltip=[
                    alt.Tooltip("age_group:N", title="연령대"),
                    alt.Tooltip("cooking_level:N", title="난이도"),
                    alt.Tooltip("recommendation_count:Q", title="추천 수"),
                    alt.Tooltip("avg_cooking_time:Q", title="평균 조리시간(분)", format=".1f"),
                ],
            )
        )
        st.altair_chart(level_chart, use_container_width=True)
        st.dataframe(
            level_df.round({"avg_cooking_time": 1, "median_cooking_time": 1}),
            use_container_width=True,
        )

    if not time_df.empty:
        st.markdown("**연령대별 조리시간 구간 비중**")
        time_chart = (
            alt.Chart(time_df)
            .mark_bar()
            .encode(
                x=alt.X("age_group:N", title="연령대"),
                y=alt.Y("counts:Q", title="건수"),
                color=alt.Color("time_bucket:N", title="조리시간 구간"),
                tooltip=["age_group", "time_bucket", "counts"],
            )
        )
        st.altair_chart(time_chart, use_container_width=True)
    else:
        st.info("조리시간 데이터를 찾을 수 없습니다.")

with ingredient_tab:
    st.subheader("연령대별 많이 보유한 재료 TOP")
    top_df = _ensure_pandas(load_age_group_ingredients(top_n))

    if top_df.empty:
        st.warning("재료 데이터가 없습니다.")
    else:
        age_groups = sorted(g for g in top_df["age_group"].unique() if pd.notna(g))
        selected_age_groups = st.multiselect(
            "연령대 선택",
            options=age_groups,
            default=age_groups,
            key="top_age_group_selector",
        )

        filtered_top_df = (
            top_df[top_df["age_group"].isin(selected_age_groups)]
            if selected_age_groups
            else pd.DataFrame(columns=top_df.columns)
        )
        filtered_top_df = _ensure_pandas(filtered_top_df)

        if filtered_top_df.empty:
            st.info("선택한 연령대에 해당하는 데이터가 없습니다.")
        else:
            st.dataframe(filtered_top_df, use_container_width=True)
            top_chart = (
                alt.Chart(filtered_top_df)
                .mark_bar(size=25)
                .encode(
                    x=alt.X("ingredient_name:N", title="재료"),
                    y=alt.Y("item_count:Q", title="보유 건수"),
                    color=alt.Color("age_group:N", title="연령대"),
                    column=alt.Column("age_group:N", title=None),
                    tooltip=["age_group", "ingredient_name", "item_count"],
                )
                .resolve_scale(x="independent")
            )
            st.altair_chart(top_chart, use_container_width=True)

    st.markdown("---")
    st.subheader("전체 인기 재료 순위")
    overall_df = _ensure_pandas(load_overall_ingredients())
    if overall_df.empty:
        st.info("재료 데이터가 부족합니다.")
    else:
        overall_chart = (
            alt.Chart(overall_df)
            .mark_bar()
            .encode(
                x=alt.X("item_count:Q", title="보유 건수"),
                y=alt.Y("ingredient_name:N", sort="-x", title="재료"),
                tooltip=["ingredient_name", "item_count"],
            )
        )
        st.altair_chart(overall_chart, use_container_width=True)

    st.markdown("---")
    st.subheader("재료 트렌드 · 계란")
    keyword_df = _ensure_pandas(load_ingredient_trend("계란", trend_window))
    if keyword_df.empty:
        st.info("계란 트렌드 데이터를 불러올 수 없습니다.")
    else:
        trend_chart = (
            alt.Chart(keyword_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("bucket:T", title="기간"),
                y=alt.Y("mentions:Q", title="등장 건수"),
                tooltip=["bucket", "mentions"],
            )
        )
        st.altair_chart(trend_chart, use_container_width=True)

with usage_tab:
    st.subheader("시간대별 앱 사용량")
    usage_df = _ensure_pandas(load_hourly_usage(start_date, end_date))
    if usage_df.empty:
        st.warning("사용 이력이 없습니다.")
    else:
        usage_chart = (
            alt.Chart(usage_df)
            .mark_line(interpolate="cardinal", point=True)
            .encode(
                x=alt.X("hour_label:N", title="시간"),
                y=alt.Y("events:Q", title="건수"),
                color=alt.Color("source:N", title="구분"),
                tooltip=["hour_label", "source", "events"],
            )
        )
        st.altair_chart(usage_chart, use_container_width=True)

        peak_hours = usage_df.groupby("hour_label")["events"].sum().sort_values(ascending=False)
        if not peak_hours.empty:
            top_peak = peak_hours.head(3)
            st.write(
                "가장 많이 사용한 시간대:",
                ", ".join(f"{label} ({count}건)" for label, count in top_peak.items()),
            )


st.caption("※ 모든 쿼리는 읽기 전용이며 서비스 트래픽에 영향을 주지 않습니다.")
