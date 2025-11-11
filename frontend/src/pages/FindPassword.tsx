import React, { useState } from "react";

import { apiFetch } from "../api/client";

export default function FindPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleReset = async () => {
    if (!email.trim()) {
      setMessage("이메일 주소를 입력해주세요.");
      return;
    }

    setLoading(true);
    try {
      const data = await apiFetch<{ message?: string }>("/reset_password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(data.message ?? "임시 비밀번호가 이메일로 발송되었습니다.");
    } catch (error) {
      console.error("임시 비밀번호 발급 실패:", error);
      const detail = error instanceof Error ? error.message : "서버 오류가 발생했습니다.";
      setMessage(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex justify-center items-center bg-[#FFFDF6]">
      <div className="w-[400px] bg-white rounded-2xl shadow-lg p-6 text-center">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">비밀번호 찾기</h2>
        <p className="text-gray-500 mb-4">가입하신 이메일로 임시 비밀번호를 보내드립니다.</p>
        <input
          type="email"
          placeholder="이메일을 입력하세요"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full p-2 border border-[#D7B78A] rounded-lg mb-4"
        />
        <button
          type="button"
          onClick={handleReset}
          disabled={loading}
          className="w-full py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg disabled:opacity-60"
        >
          {loading ? "전송 중입니다…" : "임시 비밀번호 받기"}
        </button>
        {message && <p className="mt-4 text-sm text-gray-600 whitespace-pre-line">{message}</p>}
      </div>
    </div>
  );
}
