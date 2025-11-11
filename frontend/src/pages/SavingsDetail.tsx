import React, { useEffect, useMemo, useState, type ComponentType } from "react";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

import { useAuth } from "./AuthContext";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { apiFetch } from "../api/client";

type SavingsInfo = {
  total_savings: number;
  per_recipe: Array<{
    name: string;
    count: number;
    ingredient_cost: number;
    delivery_price: number;
    savings: number;
  }>;
  notes?: string | null;
};

const TEXT = {
  nav: {
    fridge: "냉장고",
    calendar: "캘린더",
    dashboard: "대시보드",
    logout: "로그아웃",
    login: "로그인",
    myPage: "마이페이지",
  },
  title: "이번 달 절약 상세",
  description: "LLM 추정에 기반한 절약 내역입니다. 추정값이므로 실제와 다를 수 있습니다.",
  summary: {
    ingredient: "예상 재료비",
    delivery: "예상 음식값",
    savings: "절약 금액",
  },
  empty: "이번 달 완료된 레시피가 없습니다.",
  footer: {
    title: "2025 Recipe Market",
    about: "소개",
    notice: "공지사항",
    faq: "FAQ",
    contact: "Recipe Market | 123-45-6789 | +82-1234-4567",
    email: "hello@recipemarket.com",
    policy: "이용약관 | 개인정보처리방침",
  },
};

export default function SavingsDetail() {
  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;

  const [info, setInfo] = useState<SavingsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSavings = async () => {
      if (!userId) {
        setError("로그인 후 이용해 주세요.");
        setLoading(false);
        return;
      }
      try {
        const data = await apiFetch<SavingsInfo>(
          `/dashboard/monthly_savings?user_id=${encodeURIComponent(userId)}`
        );
        setInfo(data);
      } catch (fetchError) {
        console.error("Failed to fetch savings detail:", fetchError);
        setError("절약 내역을 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    };
    fetchSavings();
  }, [userId]);

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

      <main className="flex-1 px-6 pb-8 flex flex-col gap-6">
        <div className="text-center text-white drop-shadow">
          <p className="text-2xl font-extrabold tracking-tight">{TEXT.title}</p>
          <p className="text-sm font-semibold">{TEXT.description}</p>
        </div>

        {loading ? (
          <p className="text-center text-sm text-[#6B2E00]">불러오는 중...</p>
        ) : error ? (
          <p className="text-center text-sm text-red-500">{error}</p>
        ) : info && info.per_recipe.length > 0 ? (
          <section className="rounded-[32px] bg-white/85 p-6 shadow-inner text-[#6B2E00]">
            <div className="text-center mb-5">
              <p className="text-4xl font-extrabold">
                ₩{info.total_savings.toLocaleString("ko-KR")}
              </p>
              <p className="text-xs text-[#6B2E00]/70">{info.notes || ""}</p>
            </div>
            <div className="space-y-4">
              {info.per_recipe.map((item) => (
                <article
                  key={`${item.name}-${item.count}`}
                  className="rounded-3xl border border-[#E7C9A1] bg-white/90 px-5 py-4 shadow"
                >
                  <div className="flex justify-between text-sm font-semibold">
                    <span>{item.name}</span>
                    <span>{item.count}회</span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-[#6B2E00]/80">
                    <div>
                      <p className="font-semibold">{TEXT.summary.ingredient}</p>
                      <p>₩{item.ingredient_cost.toLocaleString("ko-KR")}</p>
                    </div>
                    <div>
                      <p className="font-semibold">{TEXT.summary.delivery}</p>
                      <p>₩{item.delivery_price.toLocaleString("ko-KR")}</p>
                    </div>
                    <div>
                      <p className="font-semibold">{TEXT.summary.savings}</p>
                      <p>₩{item.savings.toLocaleString("ko-KR")}</p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : (
          <p className="text-center text-sm text-[#6B2E00]/70">{TEXT.empty}</p>
        )}
      </main>

      <footer className="rounded-3xl bg-[#F6E8C9]/90 px-6 py-6 text-center text-xs text-[#6B2E00] shadow-inner mt-auto">
        <p className="text-sm font-semibold">{TEXT.footer.title}</p>
        <p className="mt-3 flex justify-center gap-4 font-medium">
          <span>{TEXT.footer.about}</span>
          <span>{TEXT.footer.notice}</span>
          <span>{TEXT.footer.faq}</span>
        </p>
        <p className="mt-3">{TEXT.footer.contact}</p>
        <p>{TEXT.footer.email}</p>
        <p className="mt-2">{TEXT.footer.policy}</p>
      </footer>
    </VideoBackgroundLayout>
  );
}
