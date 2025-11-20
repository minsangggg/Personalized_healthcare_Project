import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from db import get_conn, T


THEME_COLORS = {
    "cream": "#FFE7B8",
    "orange": "#F5B14C",
    "brown": "#A5672B",
    "beige": "#FFF6E5",
    "black": "#000000",
}


def apply_theme(fig):
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=THEME_COLORS["brown"]),
        legend=dict(bgcolor="rgba(255,255,255,0)"),
    )
    return fig


def to_age_group(dob: pd.Series) -> pd.Categorical:
    today = pd.to_datetime(date.today())
    age = (today - pd.to_datetime(dob, errors="coerce")).dt.days // 365
    bins = [-1, 19, 29, 39, 49, 59, 69, 200]
    labels = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대 이상"]
    return pd.cut(age, bins=bins, labels=labels)


def qdf(sql: str, params=None) -> pd.DataFrame:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall()
        return pd.DataFrame(rows)
    except Exception as exc:
        st.error(f"데이터 로드 실패: {exc}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_all_user_data():
    df_user = qdf(f"SELECT id, gender, date_of_birth FROM {T('user_info')}")
    df_fridge = qdf(f"SELECT id AS uid, ingredient_name FROM {T('fridge_item')}")
    df_recipe_info = qdf(f"SELECT recipe_id, ty_nm, recipe_nm_ko FROM {T('recipe')}")
    df_recommend = qdf(f"SELECT recommend_id, recipe_nm_ko, ingredient_full FROM {T('recommend_recipe')}")
    df_selected = qdf(f"SELECT id, recipe_id, recommend_id, selected_date, action FROM {T('selected_recipe')}")

    if not df_user.empty:
        df_user["gender"] = df_user["gender"].astype(str).str.strip().str.lower()
        df_user = df_user[df_user["gender"].isin(["female", "male"])].copy()
        df_user["age_group"] = to_age_group(df_user["date_of_birth"])
        df_user = df_user.dropna(subset=["age_group"])

    return df_user, df_fridge, df_recipe_info, df_selected, df_recommend


def run(user_id: str):
    st.title("👤 마이 요리 대시보드")
    st.markdown(f"**{user_id}** 님의 요리/식습관 현황이에요. 다른 사람들과 비교하여 볼까요?")
    st.markdown("---")

    df_user_all, df_fridge_all, df_recipe_info, df_selected_all, df_recommend = load_all_user_data()

    my_info = df_user_all[df_user_all["id"] == user_id]

    if my_info.empty:
        st.error("사용자 정보를 찾을 수 없습니다. (DB 확인 필요)")
        return

    my_gender = my_info["gender"].iloc[0]
    my_age_group = my_info["age_group"].iloc[0]

    group_users = df_user_all[
        (df_user_all["gender"] == my_gender) & (df_user_all["age_group"] == my_age_group)
    ].copy()

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        st.markdown("#### ① 내가 최근 7일간 자주 먹은 재료 Top N")

        st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

        N = st.slider("표시할 재료 개수", 5, 15, 7, key="my_top_n_7d")

        st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

        df_selected_all["selected_date"] = pd.to_datetime(df_selected_all["selected_date"])
        seven_days_ago = pd.Timestamp.now() - pd.Timedelta(days=7)

        my_cooked = df_selected_all[
            (df_selected_all["id"] == user_id)
            & (df_selected_all["action"] == 1)
            & (df_selected_all["selected_date"] >= seven_days_ago)
        ].copy()

        if not my_cooked.empty:
            df_merged_ingredients = my_cooked.merge(
                df_recommend[["recommend_id", "ingredient_full"]],
                on="recommend_id",
                how="inner",
            )

            if not df_merged_ingredients.empty:
                all_ingredients = df_merged_ingredients["ingredient_full"].str.split(",").explode()
                all_ingredients = all_ingredients.str.strip().replace("", pd.NA).dropna()
                all_ingredients = (
                    all_ingredients.str.split(":").str[0]
                    .str.strip()
                    .str.replace(r"[\{\}\[\]\n]+", "", regex=True)
                    .str.strip("\"'")
                    .str.strip()
                    .str.strip("\"'")
                    .str.strip()
                )
                all_ingredients = all_ingredients.replace("", pd.NA).dropna()

                if not all_ingredients.empty:
                    top_ingredients = all_ingredients.value_counts().nlargest(N).reset_index()
                    top_ingredients.columns = ["재료명", "먹은 횟수"]

                    fig1 = px.bar(
                        top_ingredients,
                        x="재료명",
                        y="먹은 횟수",
                        color_discrete_sequence=[THEME_COLORS["orange"]],
                        title=f"내가 실제로 먹은 재료 Top {N}",
                    )
                    apply_theme(fig1)
                    st.plotly_chart(fig1, width="stretch")
                else:
                    st.info("조리 완료된 레시피에 재료 정보가 명시되어 있지 않습니다.")
            else:
                st.info("조리 완료된 레시피에 해당하는 재료 정보(recommend_recipe)가 없습니다.")
        else:
            st.info("조리 완료 기록이 없어 '먹은 재료'를 집계할 수 없습니다.")

    with col2:
        st.markdown("#### ② 그룹별 최근 7일간 자주 먹은 재료 Top N")

        st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)

        st.markdown("##### 🔍 분석 그룹 선택")
        col_s1, col_s2 = st.columns(2)

        all_genders = sorted(df_user_all["gender"].unique())
        all_age_groups = sorted(df_user_all["age_group"].unique(), key=lambda x: str(x))

        my_age_group = my_info["age_group"].iloc[0]
        my_gender = my_info["gender"].iloc[0]

        default_age_idx = all_age_groups.index(my_age_group) if my_age_group in all_age_groups else 0
        default_gender_idx = all_genders.index(my_gender) if my_gender in all_genders else 0

        selected_age = col_s1.selectbox(
            "연령대",
            all_age_groups,
            index=default_age_idx,
            key="group_age_select_2",
        )

        selected_gender = col_s2.selectbox(
            "성별",
            all_genders,
            index=default_gender_idx,
            key="group_gender_select_2",
        )

        group_users = df_user_all[
            (df_user_all["gender"] == selected_gender) & (df_user_all["age_group"] == selected_age)
        ].copy()

        selected_gender_ko = "여성" if selected_gender == "female" else "남성"

        N_group = st.slider("그룹 재료 표시 개수", 5, 15, 7, key="group_top_n_7d")

        seven_days_ago = pd.Timestamp.now() - pd.Timedelta(days=7)

        group_selected = df_selected_all.merge(
            group_users[["id"]],
            left_on="id",
            right_on="id",
            how="inner",
        )

        group_cooked = group_selected[
            (group_selected["action"] == 1) & (group_selected["selected_date"] >= seven_days_ago)
        ].copy()

        if not group_cooked.empty:
            df_merged_ingredients = group_cooked.merge(
                df_recommend[["recommend_id", "ingredient_full"]],
                on="recommend_id",
                how="inner",
            )

            if not df_merged_ingredients.empty:
                all_ingredients = df_merged_ingredients["ingredient_full"].str.split(",").explode()
                all_ingredients = all_ingredients.str.strip().replace("", pd.NA).dropna()
                all_ingredients = (
                    all_ingredients.str.split(":").str[0]
                    .str.strip()
                    .str.strip("\"'")
                    .str.replace(r"[\{\}\[\]\n]+", "", regex=True)
                    .str.strip()
                    .str.strip("\"'")
                    .str.strip()
                )
                all_ingredients = all_ingredients.replace("", pd.NA).dropna()

                if not all_ingredients.empty:
                    top_ingredients = all_ingredients.value_counts().nlargest(N_group).reset_index()
                    top_ingredients.columns = ["재료명", "먹은 횟수"]

                    fig2 = px.bar(
                        top_ingredients,
                        x="재료명",
                        y="먹은 횟수",
                        color_discrete_sequence=[THEME_COLORS["brown"]],
                        title=f"나와 같은 그룹 ({selected_age} / {selected_gender_ko}) 자주 먹는 재료 Top {N_group}",
                    )
                    apply_theme(fig2)
                    st.plotly_chart(fig2, width="stretch")
                else:
                    st.info("그룹 내 조리 완료된 레시피에 재료 정보가 명시되어 있지 않습니다.")
            else:
                st.info("그룹 내 조리 완료 기록에 해당하는 재료 정보가 없습니다.")
        else:
            st.info("그룹 내 최근 7일간 조리 완료 기록이 부족합니다.")

    with col3:
        st.markdown("#### ③ 그룹별 최근 7일간 조리한 레시피 유형 분석")

        st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)

        st.markdown("##### 🔍 분석 그룹 선택")
        col_s1, col_s2 = st.columns(2)

        all_genders = sorted(df_user_all["gender"].unique())
        all_age_groups = sorted(df_user_all["age_group"].unique(), key=lambda x: str(x))

        my_age_group = my_info["age_group"].iloc[0]
        my_gender = my_info["gender"].iloc[0]
        default_age_idx = all_age_groups.index(my_age_group) if my_age_group in all_age_groups else 0
        default_gender_idx = all_genders.index(my_gender) if my_gender in all_genders else 0

        selected_age_3 = col_s1.selectbox(
            "연령대",
            all_age_groups,
            index=default_age_idx,
            key="group_age_select_3",
        )

        selected_gender_3 = col_s2.selectbox(
            "성별",
            all_genders,
            index=default_gender_idx,
            key="group_gender_select_3",
        )

        group_users_3 = df_user_all[
            (df_user_all["gender"] == selected_gender_3) & (df_user_all["age_group"] == selected_age_3)
        ].copy()

        selected_gender_ko_3 = "여성" if selected_gender_3 == "female" else "남성"

        group_selected = df_selected_all.merge(
            group_users_3[["id"]],
            left_on="id",
            right_on="id",
            how="inner",
        )

        seven_days_ago = pd.Timestamp.now() - pd.Timedelta(days=7)
        group_cooked = group_selected[
            (group_selected["action"] == 1) & (group_selected["selected_date"] >= seven_days_ago)
        ].copy()

        if not group_cooked.empty:
            df_merged_types = group_cooked.merge(
                df_recipe_info[["recipe_id", "ty_nm"]],
                on="recipe_id",
                how="inner",
            )

            if not df_merged_types.empty:
                type_counts = df_merged_types["ty_nm"].value_counts().reset_index()
                type_counts.columns = ["레시피 유형", "조리 횟수"]

                fig3 = px.bar(
                    type_counts,
                    x="조리 횟수",
                    y="레시피 유형",
                    orientation="h",
                    text_auto=True,
                    height=450,
                    color_discrete_sequence=[THEME_COLORS["brown"]],
                    title=f"그룹 ({selected_age_3} / {selected_gender_ko_3}) 레시피 유형별 조리 횟수",
                )

                fig3.update_yaxes(categoryorder="total ascending")
                fig3.update_layout(showlegend=False)

                apply_theme(fig3)
                st.plotly_chart(fig3, width="stretch")
            else:
                st.info(f"그룹 ({selected_age_3} / {selected_gender_ko_3})의 조리 기록에 해당하는 레시피 유형 정보가 부족합니다.")
        else:
            st.info(f"그룹 ({selected_age_3} / {selected_gender_ko_3})의 최근 7일간 조리 완료 기록이 부족합니다.")

    with col4:
        st.markdown("#### ④ 나의 요리 전환율 (최근 7일)")

        seven_days_ago = pd.Timestamp.now() - pd.Timedelta(days=7)
        my_selected_7d = df_selected_all[
            (df_selected_all["id"] == user_id) & (df_selected_all["selected_date"] >= seven_days_ago)
        ].copy()

        my_total_logs = len(my_selected_7d)
        my_converted = int((my_selected_7d["action"] == 1).sum())
        my_conversion_rate = (my_converted / my_total_logs * 100) if my_total_logs > 0 else 0.0

        st.metric(
            label="나의 실제 요리 전환율",
            value=f"{my_conversion_rate:.1f}%",
            delta=f"총 {my_total_logs}건 중 {my_converted}건 완료",
        )

        st.markdown("---")

        st.markdown("##### 👥 다른 그룹 전환율 탐색")

        col_s1, col_s2 = st.columns(2)
        all_genders = sorted(df_user_all["gender"].unique())
        all_age_groups = sorted(df_user_all["age_group"].unique(), key=lambda x: str(x))

        my_age_group = my_info["age_group"].iloc[0]
        my_gender = my_info["gender"].iloc[0]
        default_age_idx = all_age_groups.index(my_age_group) if my_age_group in all_age_groups else 0
        default_gender_idx = all_genders.index(my_gender) if my_gender in all_genders else 0

        explore_age = col_s1.selectbox(
            "연령대 선택",
            all_age_groups,
            index=default_age_idx,
            key="explore_age_select",
        )

        explore_gender = col_s2.selectbox(
            "성별 선택",
            all_genders,
            index=default_gender_idx,
            key="explore_gender_select",
        )

        explore_group_users = df_user_all[
            (df_user_all["gender"] == explore_gender) & (df_user_all["age_group"] == explore_age)
        ].copy()

        explore_gender_ko = "여성" if explore_gender == "female" else "남성"

        explore_selected_7d = df_selected_all.merge(
            explore_group_users[["id"]],
            on="id",
            how="inner",
        )

        explore_selected_7d = explore_selected_7d[
            explore_selected_7d["selected_date"] >= seven_days_ago
        ].copy()

        if not explore_selected_7d.empty:
            total_logs = len(explore_selected_7d)
            converted_count = int((explore_selected_7d["action"] == 1).sum())
            conversion_rate = (converted_count / total_logs * 100) if total_logs > 0 else 0.0

            df_conv = pd.DataFrame(
                {
                    "label": ["조리 완료", "미조리/미확정"],
                    "value": [converted_count, total_logs - converted_count],
                }
            )

            st.subheader(f"그룹 ({explore_age} / {explore_gender_ko}) 전환율")

            c1, c2 = st.columns(2)
            c1.metric("총 선택 건수", f"{total_logs:,}")
            c2.metric("전환율", f"{conversion_rate:.1f}%")

            fig4 = px.pie(
                df_conv,
                names="label",
                values="value",
                title=" ",
                hole=0.5,
                color="label",
                color_discrete_map={
                    "조리 완료": THEME_COLORS["brown"],
                    "미조리/미확정": THEME_COLORS["beige"],
                },
            )

            fig4.update_traces(
                textposition="inside",
                textinfo="percent",
                textfont_size=18,
                textfont_weight="bold",
                insidetextorientation="horizontal",
            )
            apply_theme(fig4)

            st.plotly_chart(fig4, width="stretch")
        else:
            st.info(f"그룹 ({explore_age} / {explore_gender_ko})의 최근 7일간 선택 기록이 없습니다.")

    st.markdown("---")
    st.caption("※ 이 화면은 예시입니다. 나중에 streak, 뱃지, 영양제 통계 등도 여기 추가하면 돼요.")
