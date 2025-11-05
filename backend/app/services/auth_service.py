import random
import string

from fastapi import HTTPException

from app.db.connection import connection_scope
from app.schemas.auth import LoginRequest, ResetPasswordRequest, SignupRequest
from app.utils.email import send_email


def signup(user: SignupRequest) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_info WHERE ID = %s", (user.id,))
                existing = cur.fetchone()
                if existing:
                    raise HTTPException(status_code=400, detail="User ID already exists.")

                sql = (
                    """
                    INSERT INTO user_info (id, user_name, gender, email, date_of_birth, password, goal, cooking_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                )
                cur.execute(
                    sql,
                    (
                        user.id,
                        user.user_name,
                        user.gender,
                        user.email,
                        user.date_of_birth,
                        user.password,
                        user.goal,
                        user.cooking_level,
                    ),
                )
            conn.commit()
        return {"message": "Signup successful."}
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Server error: {exc}") from exc


def login(user: LoginRequest) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                sql = "SELECT * FROM user_info WHERE id = %s AND password = %s"
                cur.execute(sql, (user.ID, user.PASSWORD))
                result = cur.fetchone()
                if result:
                    return {"message": "Login successful", "name": result["user_name"]}
        raise HTTPException(status_code=401, detail="Invalid ID or password.")
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Server error: {exc}") from exc


def reset_password(request: ResetPasswordRequest) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, user_name FROM user_info WHERE email = %s", (request.email,))
                user = cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="No user found for the provided email.")

                temp_password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
                cur.execute("UPDATE user_info SET password = %s WHERE email = %s", (temp_password, request.email))
            conn.commit()

        body = (
            f"Hello {user['user_name']}!\n\n"
            f"Your temporary password is: {temp_password}\n\n"
            "Please log in and change your password immediately."
        )
        send_email(request.email, "CookUS Temporary Password", body)

        return {"message": f"A temporary password has been sent to {request.email}."}
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Server error: {exc}") from exc
