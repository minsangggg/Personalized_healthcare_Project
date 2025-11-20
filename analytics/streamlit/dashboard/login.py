import os
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Optional, Tuple

import jwt
import streamlit as st
from dotenv import load_dotenv

from db import query_one, T

load_dotenv(Path(__file__).with_name(".env"))

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:
    get_script_run_ctx = None

try:
    from streamlit.web.server.websocket_headers import _get_websocket_headers as _streamlit_ws_headers
except Exception:
    _streamlit_ws_headers = None


VALID_ADMIN_ID = "admin1234"
VALID_ADMIN_PW = "admin1234"

SESSION_KEY = "cookus_authenticated"
SESSION_USER_KEY = "cookus_username"
SESSION_ROLE_KEY = "cookus_role"
JWT_COOKIE_NAME = "cookus_jwt"
JWT_QUERY_PARAM = "token"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def _load_jwt_secret() -> Optional[str]:
    return os.getenv("JWT_SECRET")


JWT_SECRET = _load_jwt_secret()


def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def _get_cookie_value(name: str) -> Optional[str]:
    headers = None
    context = getattr(st, "context", None)
    if context is not None:
        headers = getattr(context, "headers", None)
        if callable(headers):
            headers = headers()
    if headers is None and _streamlit_ws_headers is not None and get_script_run_ctx is not None:
        ctx = get_script_run_ctx()
        if ctx is not None:
            try:
                headers = _streamlit_ws_headers(ctx.session_id)
            except TypeError:
                headers = _streamlit_ws_headers()
            except Exception:
                headers = None
    if not headers:
        return None
    cookie_header = headers.get("Cookie") if hasattr(headers, "get") else None
    if not cookie_header:
        return None
    jar = SimpleCookie()
    jar.load(cookie_header)
    morsel = jar.get(name)
    return morsel.value if morsel else None


def _extract_jwt_from_request() -> Tuple[Optional[str], bool]:
    params = dict(st.query_params)
    query_value = params.get(JWT_QUERY_PARAM)
    token: Optional[str] = None
    if isinstance(query_value, list):
        token = query_value[0] if query_value else None
    elif isinstance(query_value, str):
        token = query_value
    elif query_value is not None:
        token = str(query_value)
    if token:
        return token, True
    cookie_token = _get_cookie_value(JWT_COOKIE_NAME)
    if cookie_token:
        return cookie_token, False
    return None, False


def _clear_token_from_url():
    params = dict(st.query_params)
    if JWT_QUERY_PARAM not in params:
        return
    params.pop(JWT_QUERY_PARAM, None)
    st.query_params = params


def auto_login_from_jwt() -> bool:
    if st.session_state.get(SESSION_KEY):
        return False

    token, from_query = _extract_jwt_from_request()
    if not token or not JWT_SECRET:
        return False

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        st.warning("세션이 만료되었습니다. 다시 로그인 해주세요.")
        return False
    except jwt.InvalidTokenError:
        st.warning("로그인 정보가 올바르지 않습니다. 다시 로그인 해주세요.")
        return False

    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        return False

    role = payload.get("role", "user")
    st.session_state[SESSION_KEY] = True
    st.session_state[SESSION_USER_KEY] = user_id
    st.session_state[SESSION_ROLE_KEY] = role if role in ("admin", "user") else "user"

    if from_query:
        _clear_token_from_url()
    return True


def authenticate_user_from_db(user_id: str, password: str) -> bool:
    sql = f"""
    SELECT password
    FROM {T('user_info')}
    WHERE id = %s
    """
    user = query_one(sql, (user_id,))
    if user and user.get("password") == password:
        return True
    return False


def ensure_login() -> bool:
    if auto_login_from_jwt():
        return True

    authed = st.session_state.get(SESSION_KEY, False)

    if authed:
        username = st.session_state.get(SESSION_USER_KEY, "사용자")
        role = st.session_state.get(SESSION_ROLE_KEY, "user")
        role_ko = "운영자" if role == "admin" else "일반 사용자"

        st.sidebar.success(f"✅ {username}님 로그인됨 ({role_ko})")
        if st.sidebar.button("로그아웃"):
            st.session_state.pop(SESSION_KEY, None)
            st.session_state.pop(SESSION_USER_KEY, None)
            st.session_state.pop(SESSION_ROLE_KEY, None)
            rerun()
        return True

    st.title("🔐 Cookus 서비스 로그인")
    st.caption("아이디와 비밀번호를 입력해 주세요.")

    with st.form("cookus-login", clear_on_submit=False):
        user_id = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        if user_id == VALID_ADMIN_ID and password == VALID_ADMIN_PW:
            st.session_state[SESSION_KEY] = True
            st.session_state[SESSION_USER_KEY] = user_id
            st.session_state[SESSION_ROLE_KEY] = "admin"
            st.success("관리자 로그인 성공! 좌측 메뉴를 통해 이동하세요.")
            rerun()
        elif authenticate_user_from_db(user_id, password):
            st.session_state[SESSION_KEY] = True
            st.session_state[SESSION_USER_KEY] = user_id
            st.session_state[SESSION_ROLE_KEY] = "user"
            st.success("사용자 로그인 성공! 마이 대시보드로 이동합니다.")
            rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    else:
        st.info("아이디와 비밀번호를 입력해 주세요.")

    return False
