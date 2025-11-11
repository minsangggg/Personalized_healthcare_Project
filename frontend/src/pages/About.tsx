import React, { type ComponentType } from "react";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { useAuth } from "./AuthContext";

const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;

const TEXT = {
  nav: {
    fridge: "냉장고",
    calendar: "캘린더",
    dashboard: "대시보드",
    logout: "로그아웃",
    login: "로그인",
  },
  hero: {
    title: "소개",
    subtitle:
      "이 웹앱은 사용자의 금전적, 시간적인 문제를 고려하여 레시피를 추천해주기 위해 개발되었습니다.",
    stats: [
      { label: "예산 절감", value: "30%", caption: "평균/장보기/비용절감" },
      { label: "준비 시간", value: "15분", caption: "한 끼/완성까지" },
      { label: "맞춤 추천", value: "4만+", caption: "누적/레시피/완성" },
    ],
  },
  timeline: {
    title: "우리의 여정",
    items: [
      { year: "2022", title: "아이디어 구상", detail: "사용자 냉장고 데이터를 활용한 맞춤형 레시피 구상" },
      { year: "2023", title: "베타 서비스", detail: "초기 사용자 1,000명과 함께 추천 정확도 학습" },
      { year: "2024", title: "정식 런칭", detail: "LLM 기반 조리 순서 클린업과 YouTube 쇼츠 연동" },
      { year: "2025", title: "오늘", detail: "맞춤 레시피와 함께 생활을 더 가볍게 만드는 중" },
    ],
  },
  personas: {
    title: "CookUS와 함께하는\n사람들",
    cards: [
      {
        title: "바쁜 직장인",
        description: "퇴근 후 15분 안에 완성할 수 있는 메뉴를 추천받아요.",
        image: "/man.jpg",
      },
      {
        title: "혼밥 자취생",
        description: "냉장고에 있는 재료만으로 한 끼를 해결합니다.",
        image: "/woman.jpg",
      },
      {
        title: "재테크를 챙기는 주부",
        description: "장보기 예산을 줄이기 위한 재료 활용법을 받아요.",
        image: "/stock.jpg",
      },
      {
        title: "손주를 돌보는 할머니",
        description: "건강하고 단순한 메뉴로 가족 식탁을 책임져요.",
        image: "/grandma.jpg",
      },
    ],
  },
  closing: {
    title: "당신의 부엌에서 시작되는 변화",
    message: "CookUS는 오늘도 사용자의 하루를 가볍게 만들 레시피를 준비합니다.",
  },
  footer: {
    title: "2025 레시피 마켓",
    about: "소개",
    faq: "FAQ",
    company: "레시피 마켓 | 대표자 홍길동",
    contact: "123-45-6789 (사업자정보확인) | +82-1234-4567",
    email: "parkms@gmail.com",
    policy: "이용약관 | 개인정보처리방침",
  },
};

export default function AboutPage() {
  const { user, logout } = useAuth();

  return (
    <VideoBackgroundLayout contentClassName="text-[#6B2E00]">
      <header className="relative pt-6 pb-4 text-center">
        <h1 className="text-xl font-extrabold tracking-wide">CookUS</h1>
        <nav className="mt-3 flex items-center justify-center gap-5 text-sm font-semibold">
          <Link to="/" className="hover:text-[#8B4000]">
            {TEXT.nav.fridge}
          </Link>
          <span>|</span>
          <Link to="/calendar" className="hover:text-[#8B4000]">
            {TEXT.nav.calendar}
          </Link>
          <span>|</span>
          <Link to="/dashboard" className="hover:text-[#8B4000]">
            {TEXT.nav.dashboard}
          </Link>
          <span>|</span>
          {user ? (
            <button onClick={logout} className="hover:text-[#8B4000]">
              {TEXT.nav.logout}
            </button>
          ) : (
            <Link to="/login" className="hover:text-[#8B4000]">
              {TEXT.nav.login}
            </Link>
          )}
        </nav>
        <Link
          to="/mypage"
          className="absolute right-6 top-3 flex items-center justify-center hover:text-[#8B4000] transition"
        >
          <UserCircleIcon className={`h-8 w-8 ${user ? "text-[#6B2E00]" : "text-gray-400"}`} />
        </Link>
      </header>

      <main className="flex-1 px-6 pb-8 flex flex-col space-y-8 mt-6">
        <section className="min-h-[60vh] rounded-[32px] relative overflow-hidden shadow-inner text-[#6B2E00]">
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url(/aboutus.jpg)" }}
          />
          <div className="absolute inset-0 bg-white/60" />
          <div className="relative z-10 p-8">
            <div>
              <p className="text-3xl font-extrabold tracking-tight">{TEXT.hero.title}</p>
              <p className="mt-4 text-lg font-semibold leading-relaxed">{TEXT.hero.subtitle}</p>
            </div>
            <div className="mt-10 grid grid-cols-1 gap-6 text-center sm:grid-cols-3">
              {TEXT.hero.stats.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-3xl bg-[#FCE7C8] px-6 py-6 transition hover:bg-[#F7D98A]"
                >
                  <p className="text-base font-semibold tracking-wide text-[#8C5C2D]">
                    {stat.label}
                  </p>
                  <p className="mt-2 text-3xl font-extrabold text-[#6B2E00]">{stat.value}</p>
                  <p className="mt-1 text-xs text-[#8C5C2D]">
                    {stat.caption.split("/").map((line, idx) => (
                      <span key={`${stat.label}-cap-${idx}`} className="block whitespace-nowrap">
                        {line}
                      </span>
                    ))}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="min-h-[80vh] rounded-[32px] relative overflow-hidden shadow-xl">
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url(/stock.jpg)" }}
          />
          <div className="absolute inset-0 bg-[#F6E8C9]/80" />
          <div className="relative z-10 flex h-full flex-col p-8 text-[#6B2E00]">
            <div className="text-center leading-tight">
              <p className="text-3xl font-extrabold whitespace-pre-line">{TEXT.personas.title}</p>
            </div>
            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {TEXT.personas.cards.map((card) => (
                <article
                  key={card.title}
                  className="rounded-3xl bg-white/90 p-4 shadow transition hover:shadow-lg"
                >
                  <div
                    className="h-32 rounded-2xl bg-cover bg-center"
                    style={{ backgroundImage: `url(${card.image})` }}
                  />
                  <h3 className="mt-4 text-lg font-bold">{card.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed">{card.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <footer className="mt-6 rounded-3xl bg-[#F6E8C9]/90 px-6 py-6 text-center text-xs text-[#6B2E00] shadow-inner">
          <p className="text-sm font-semibold">{TEXT.footer.title}</p>
          <p className="mt-3 flex justify-center gap-4 font-medium">
            <span className="font-bold underline underline-offset-4">{TEXT.footer.about}</span>
            <Link to="/faq" className="hover:text-[#8B4000]">
              {TEXT.footer.faq}
            </Link>
          </p>
          <p className="mt-3">{TEXT.footer.company}</p>
          <p>{TEXT.footer.contact}</p>
          <p>{TEXT.footer.email}</p>
          <p className="mt-2">{TEXT.footer.policy}</p>
        </footer>
      </main>
    </VideoBackgroundLayout>
  );
}
