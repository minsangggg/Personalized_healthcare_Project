import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "./AuthContext";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";

export default function Login() {
  const [idInput, setIdInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async () => {
    const trimmedId = idInput.trim();
    const trimmedPassword = passwordInput.trim();

    if (!trimmedId || !trimmedPassword) {
      alert("아이디와 비밀번호를 모두 입력해 주세요.");
      return;
    }

    try {
      const data = await apiFetch<{ name?: string; user_name?: string }>("/login", {
        method: "POST",
        body: JSON.stringify({
          ID: trimmedId,
          PASSWORD: trimmedPassword,
        }),
      });

      const displayName = data.name || data.user_name || trimmedId;
      login({ id: trimmedId, name: displayName });
      alert(`${displayName}님, 환영합니다!`);
      navigate("/");
    } catch (error) {
      console.error("로그인 오류:", error);
      const message =
        error instanceof Error ? error.message : "로그인을 진행하지 못했습니다. 잠시 후 다시 시도해 주세요.";
      alert(message);
    }
  };

  return (
    <VideoBackgroundLayout contentClassName="px-6 py-8">
      <div className="flex h-full w-full flex-col text-white">
        <header className="text-center text-[#6B2E00]">
          <h1 className="text-2xl font-extrabold tracking-wide drop-shadow-sm">CookUS</h1>
          <nav className="mt-4 flex items-center justify-center gap-3 text-sm font-semibold tracking-wider">
            {["냉장고", "캘린더", "대시보드", "로그인"].map((label, index) => (
              <React.Fragment key={label}>
                {index !== 0 && <span className="text-[#B8854E]">|</span>}
                <Link
                  to={
                    label === "냉장고"
                      ? "/"
                      : label === "캘린더"
                        ? "/calendar"
                        : label === "대시보드"
                          ? "/dashboard"
                          : "/login"
                  }
                  className={`${
                    label === "로그인" ? "text-[#8B4000]" : "text-[#6B2E00]"
                  } hover:text-[#8B4000] transition-colors`}
                >
                  {label}
                </Link>
              </React.Fragment>
            ))}
          </nav>
        </header>

        <section className="mt-10 text-center">
          <p className="text-lg font-semibold drop-shadow">냉장고 속 재료로</p>
          <p className="text-2xl font-extrabold tracking-tight drop-shadow">레시피를 추천받아요.</p>
        </section>

        <section className="mt-10 flex justify-center">
          <div className="w-full max-w-sm rounded-[36px] bg-[#FCF4E2]/95 px-6 py-8 text-center text-[#6B2E00] shadow-[0_18px_45px_rgba(107,46,0,0.25)]">
            <p className="text-sm font-semibold text-[#B8854E]">내 계정으로 로그인</p>
            <div className="mt-6 space-y-3 text-left">
              <input
                type="text"
                placeholder="아이디"
                value={idInput}
                onChange={(event) => setIdInput(event.target.value)}
                className="w-full rounded-2xl border border-[#E1C9A3] bg-white/90 px-4 py-3 text-sm text-[#6B2E00] focus:border-transparent focus:ring-2 focus:ring-[#F5B76B]"
              />
              <input
                type="password"
                placeholder="비밀번호"
                value={passwordInput}
                onChange={(event) => setPasswordInput(event.target.value)}
                className="w-full rounded-2xl border border-[#E1C9A3] bg-white/90 px-4 py-3 text-sm text-[#6B2E00] focus:border-transparent focus:ring-2 focus:ring-[#F5B76B]"
              />
            </div>
            <button
              type="button"
              onClick={handleLogin}
              className="mt-6 w-full rounded-full bg-[#F2994A] px-6 py-3 text-base font-semibold text-white shadow-[0_6px_20px_rgba(240,138,41,0.45)] transition hover:bg-[#f08a29]"
            >
              로그인
            </button>
            <div className="mt-6 flex items-center justify-center gap-3 text-sm text-[#8C5C2D]">
              <Link to="/find-id" className="hover:underline">
                아이디 찾기
              </Link>
              <span>|</span>
              <Link to="/find-password" className="hover:underline">
                비밀번호 찾기
              </Link>
              <span>|</span>
              <Link to="/signup" className="hover:underline">
                회원가입
              </Link>
            </div>
          </div>
        </section>

        <section className="mt-auto">
          <div className="mt-10 rounded-[28px] bg-[#FCF4E2]/90 px-6 py-6 text-center text-[#6B2E00] shadow-[0_12px_30px_rgba(107,46,0,0.15)]">
            <h2 className="text-base font-extrabold mb-2">2025 레시피 마켓</h2>
            <div className="mb-3 flex justify-center gap-6 text-sm text-[#8C5C2D]">
              <a href="#about" className="hover:text-[#8B4000]">
                소개
              </a>
              <a href="#notice" className="hover:text-[#8B4000]">
                공지사항
              </a>
              <a href="#faq" className="hover:text-[#8B4000]">
                FAQ
              </a>
            </div>
            <p className="text-xs leading-relaxed text-[#8C5C2D]">
              레시피 마켓 | 대표자 홍길동
              <br />
              123-45-6789 (사업자정보확인) | +82-1234-4567
              <br />
              parkms@gmail.com
            </p>
            <p className="mt-3 text-xs text-[#8B4000]">이용약관 | 개인정보처리방침</p>
          </div>
        </section>
      </div>
    </VideoBackgroundLayout>
  );
}
