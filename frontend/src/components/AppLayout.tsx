import React from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

export default function AppLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen flex justify-center bg-[#FFFDF6] py-6">
      <div className="w-[430px] min-h-[95vh] bg-[#F7D98A] rounded-2xl shadow-lg flex flex-col overflow-y-auto">
        {/* 🔹 상단 고정 헤더 */}
        <header className="bg-[#F7D98A] border-b border-[#D7B78A] text-center pt-4 pb-2 sticky top-0 z-10">
          <h1 className="text-[#6B2E00] text-xl font-extrabold">CookUS</h1>
          <nav className="flex justify-center gap-6 text-[#6B2E00] font-medium text-[15px] mt-2">
            <Link
              to="/"
              className={
                location.pathname === "/"
                  ? "font-bold text-[#8B4000]"
                  : "hover:text-[#8B4000]"
              }
            >
              냉장고
            </Link>
            <span>|</span>
            <Link
              to="/calendar"
              className={
                location.pathname === "/calendar"
                  ? "font-bold text-[#8B4000]"
                  : "hover:text-[#8B4000]"
              }
            >
              캘린더
            </Link>
            <span>|</span>
            <Link
              to="/dashboard"
              className="hover:text-[#8B4000]"
            >
              대시보드
            </Link>
            <span>|</span>
            <Link
              to="/login"
              className="hover:text-[#8B4000]"
            >
              로그인
            </Link>
          </nav>
        </header>

        {/* 🔸 메인 콘텐츠 영역 */}
        <main className="flex-1 flex flex-col items-center justify-center px-6 py-8">
          <Outlet /> {/* 👈 여기에 각 페이지가 표시됨 */}
        </main>

        {/* 🔹 공통 푸터 */}
        <footer className="bg-[#F7D98A] text-center text-[#6B2E00] border-t border-[#D7B78A] py-6 rounded-b-2xl">
          <h2 className="text-base font-extrabold mb-1">2025 레시피 마켓</h2>
          <div className="flex justify-center gap-6 text-sm mb-4">
            <a href="#guide" className="hover:text-[#8B4000]">예정</a>
            <a href="#notice" className="hover:text-[#8B4000]">공지사항</a>
            <a href="#reserve" className="hover:text-[#8B4000]">추천받기</a>
          </div>
          <p className="text-xs leading-relaxed">
            레시피 마켓 | 대표자 홍길동 <br />
            123-45-6789 [사업자정보확인] | +82-1234-4567 <br />
            jejufarmersmarket@gmail.com
          </p>
          <p className="text-xs text-[#8B4000] mt-2">이용약관 | 개인정보처리방침</p>
        </footer>
      </div>
    </div>
  );
}
