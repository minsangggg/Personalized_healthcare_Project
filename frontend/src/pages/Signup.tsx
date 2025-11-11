import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiFetch } from "../api/client";

type SignupForm = {
  id: string;
  name: string;
  password: string;
  email: string;
  birth: string;
  gender: string;
  level: string;
  goal: string;
};

const emptyForm: SignupForm = {
  id: "",
  name: "",
  password: "",
  email: "",
  birth: "",
  gender: "",
  level: "",
  goal: "",
};

const genderOptions = [
  { value: "male", label: "남성" },
  { value: "female", label: "여성" },
];

const levelOptions = [
  { value: "하", label: "하" },
  { value: "상", label: "상" },
];

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState<SignupForm>(emptyForm);
  const [submitting, setSubmitting] = useState(false);

  const handleChange =
    (field: keyof SignupForm) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleSubmit = async () => {
    if (Object.values(form).some((value) => !value.trim())) {
      alert("모든 항목을 입력해 주세요.");
      return;
    }

    const goalValue = Number(form.goal);
    if (!Number.isFinite(goalValue) || goalValue <= 0) {
      alert("목표 칼로리를 양수로 입력해 주세요.");
      return;
    }

    setSubmitting(true);

    try {
      await apiFetch("/signup", {
        method: "POST",
        body: JSON.stringify({
          id: form.id.trim(),
          user_name: form.name.trim(),
          password: form.password,
          email: form.email.trim(),
          date_of_birth: form.birth,
          gender: form.gender,
          cooking_level: form.level,
          goal: goalValue,
        }),
      });

      alert("회원가입이 완료되었습니다. 로그인해 주세요.");
      setForm(emptyForm);
      navigate("/login");
    } catch (error) {
      console.error("Signup failed:", error);
      const message =
        error instanceof Error ? error.message : "회원가입 중 문제가 발생했습니다.";
      alert(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex justify-center bg-[#FFFDF6] py-6 overflow-y-auto">
      <div className="w-[430px] min-h-[95vh] bg-[#F7D98A] rounded-2xl shadow-lg flex flex-col overflow-y-auto">
        <header className="bg-[#F7D98A] border-b border-[#D7B78A] text-center pt-4 pb-2 sticky top-0 z-50">
          <h1 className="text-[#6B2E00] text-xl font-extrabold">CookUS</h1>
          <nav className="flex justify-center gap-6 text-[#6B2E00] font-medium text-[15px] mt-2">
            <Link to="/" className="hover:text-[#8B4000]">
              메인
            </Link>
            <span>|</span>
            <Link to="/calendar" className="hover:text-[#8B4000]">
              캘린더
            </Link>
            <span>|</span>
            <Link to="/dashboard" className="hover:text-[#8B4000]">
              대시보드
            </Link>
            <span>|</span>
            <Link to="/login" className="hover:text-[#8B4000]">
              로그인
            </Link>
          </nav>
        </header>

        <main className="flex-1 flex flex-col items-center justify-center px-6 py-8">
          <h2 className="text-[#6B2E00] text-2xl font-bold mb-6">회원가입</h2>
          <p className="text-[#6B2E00]/80 text-sm mb-4 text-center">
            CookUS와 함께 취향에 맞는 레시피 추천을 받아보세요.
          </p>

          <input
            type="text"
            placeholder="아이디"
            value={form.id}
            onChange={handleChange("id")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          />

          <input
            type="text"
            placeholder="이름"
            value={form.name}
            onChange={handleChange("name")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          />

          <input
            type="password"
            placeholder="비밀번호"
            value={form.password}
            onChange={handleChange("password")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          />

          <input
            type="email"
            placeholder="이메일"
            value={form.email}
            onChange={handleChange("email")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          />

          <input
            type="date"
            value={form.birth}
            onChange={handleChange("birth")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          />

          <select
            value={form.gender}
            onChange={handleChange("gender")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          >
            <option value="">성별 선택</option>
            {genderOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <select
            value={form.level}
            onChange={handleChange("level")}
            className="w-72 px-4 py-2 mb-3 rounded-lg border border-[#D7B78A]"
          >
            <option value="">요리 레벨 선택</option>
            {levelOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <input
            type="number"
            placeholder="주간 레시피 달성 횟수 (예: 4)"
            value={form.goal}
            onChange={handleChange("goal")}
            className="w-72 px-4 py-2 mb-6 rounded-lg border border-[#D7B78A]"
          />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="bg-[#F2994A] hover:bg-[#f08a29] text-white font-semibold px-6 py-2 rounded-lg shadow disabled:opacity-60"
          >
            {submitting ? "가입 중..." : "가입하기"}
          </button>
        </main>

        <footer className="bg-[#F7D98A] text-center text-[#6B2E00] border-t border-[#D7B78A] py-6">
          <h2 className="text-base font-extrabold mb-1">2025 Recipe Market</h2>
          <p className="text-xs leading-relaxed">
            Recipe Market | 123-45-6789 | +82-1234-4567 <br /> hello@recipemarket.com
          </p>
          <p className="text-xs text-[#8B4000] mt-2">이용약관 | 개인정보처리방침</p>
        </footer>
      </div>
    </div>
  );
}
