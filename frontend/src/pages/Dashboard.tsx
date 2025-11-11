import React, { useEffect, useMemo, useState, type ComponentType } from "react";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

import { useAuth } from "./AuthContext";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { apiFetch } from "../api/client";

const TEXT = {
  nav: {
    fridge: "\uB0C9\uC7A5\uACE0",
    calendar: "\uCE98\uB9B0\uB354",
    dashboard: "\uB300\uC2DC\uBCF4\uB4DC",
    logout: "\uB85C\uADF8\uC544\uC6C3",
    login: "\uB85C\uADF8\uC778",
    myPage: "\uB9C8\uC774\uD398\uC774\uC9C0",
  },
  title: "\uB808\uC2DC\uD53C \uB9C8\uCF13 \uB300\uC2DC\uBCF4\uB4DC",
  description: "\uB808\uC2DC\uD53C \uB9C8\uCF13\uC758 \uB370\uC774\uD130 \uC9C0\uD5A5\uC744 \uC9C0\uC18D \uC5C5\uB370\uC774\uD2B8 \uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.",
  savingsCards: [
    {
      title: "\uC6D4\uBCC4 \uC694\uB9AC \uD69F\uC218",
      key: "monthly",
      accent: "bg-[#FFF3E0] text-[#9A4E00]",
    },
    {
      title: "\uC808\uC57D\uD55C \uBE44\uC6A9",
      key: "cost",
      accent: "bg-[#DFF5E6] text-[#1B7B3A]",
    },
    {
      title: "\uC808\uC57D\uD55C \uBC30\uB2EC \uBE44\uC6A9",
      key: "delivery",
      accent: "bg-[#E7F0FF] text-[#1F4E8C]",
    },
  ],
  footer: {
    title: "2025 Recipe Market",
    about: "\uC18C\uAC1C",
    notice: "\uACF5\uC9C0\uC0AC\uD56D",
    faq: "FAQ",
    contact: "Recipe Market | 123-45-6789 | +82-1234-4567",
    email: "hello@recipemarket.com",
    policy: "\uC774\uC6A9\uC57D\uAD00 | \uAC1C\uC778\uC815\uBCF4\uCC98\uB9AC\uBC29\uCE68",
  },
};
const DONUT_COLORS = ["#d96881", "#f3a87d", "#f7cf66"];

export default function Dashboard() {
  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;
  const [monthlyCount, setMonthlyCount] = useState<number>(0);
  const [totalSavings, setTotalSavings] = useState<number>(0);
  const [savingsNote, setSavingsNote] = useState<string>("");
  const [ingredientsTop, setIngredientsTop] = useState<Array<{ name: string; count: number }>>([]);

  useEffect(() => {
    const fetchMonthlyCount = async () => {
      if (!userId) {
        setMonthlyCount(0);
        return;
      }
      try {
        const data = await apiFetch<{ completed_count?: number }>(
          `/selected_recipe/monthly_completed?user_id=${encodeURIComponent(userId)}`
        );
        setMonthlyCount(typeof data.completed_count === "number" ? data.completed_count : 0);
      } catch (error) {
        console.error("Failed to fetch monthly completed recipes:", error);
        setMonthlyCount(0);
      }
    };
    fetchMonthlyCount();
  }, [userId]);

  useEffect(() => {
    const fetchSavings = async () => {
      if (!userId) {
        setTotalSavings(0);
        setSavingsNote("");
        return;
      }
      try {
        const data = await apiFetch<{ total_savings?: number; notes?: string; ingredients_top?: Array<{ name: string; count: number }> }>(
          `/dashboard/monthly_savings?user_id=${encodeURIComponent(userId)}`
        );
        setTotalSavings(typeof data.total_savings === "number" ? data.total_savings : 0);
        setSavingsNote(typeof data.notes === "string" ? data.notes : "");
        setIngredientsTop(Array.isArray(data.ingredients_top) ? data.ingredients_top : []);
      } catch (error) {
        console.error("Failed to fetch monthly savings:", error);
        setTotalSavings(0);
        setSavingsNote("");
        setIngredientsTop([]);
      }
    };
    fetchSavings();
  }, [userId]);

  return (
    <VideoBackgroundLayout contentClassName="text-[#6B2E00]">
      <header className="relative bg-transparent text-center pt-4 pb-2 sticky top-0 z-50">
        <h1 className="text-xl font-extrabold">CookUS</h1>
        <nav className="mt-2 flex justify-center gap-6 text-sm font-medium">
          <Link to="/" className="hover:text-[#8B4000]">
            {TEXT.nav.fridge}
          </Link>
          <span>|</span>
          <Link to="/calendar" className="hover:text-[#8B4000]">
            {TEXT.nav.calendar}
          </Link>
          <span>|</span>
          <Link to="/dashboard" className="font-bold text-[#8B4000]">
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

      <main className="flex-1 flex flex-col items-center px-6 py-8 gap-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-3">{TEXT.title}</h2>
          <p className="text-[#6B2E00]/80 text-sm">{TEXT.description}</p>
        </div>
        <div className="flex flex-col w-full max-w-4xl gap-4 px-10">
          {TEXT.savingsCards.map((card) => {
            let displayValue = "";
            let extraNote: string | null = null;
            switch (card.key) {
              case "monthly":
                displayValue = `${monthlyCount}회`;
                break;
              case "cost":
                displayValue = `₩${totalSavings.toLocaleString("ko-KR")}`;
                extraNote = savingsNote;
                break;
              case "delivery":
                displayValue = `₩${(monthlyCount * 3000).toLocaleString("ko-KR")}`;
                break;
              default:
                displayValue = "-";
            }

            const Content = (
              <>
                <p className="text-xs font-semibold text-[#6B2E00]/70">{card.title}</p>
                <p className="mt-0.5 text-3xl font-extrabold leading-tight">{displayValue}</p>
                {extraNote && (
                  <p className="mt-1 text-xs text-[#6B2E00]/70 whitespace-pre-line">{extraNote}</p>
                )}
              </>
            );

            if (card.key === "cost") {
              return (
                <Link
                  key={card.title}
                  to="/savings-detail"
                  className={`rounded-3xl px-6 py-5 shadow-lg border border-white/60 ${card.accent} block hover:opacity-95 transition`}
                >
                  {Content}
                </Link>
              );
            }

            return (
              <div
                key={card.title}
                className={`rounded-3xl px-6 py-5 shadow-lg border border-white/60 ${card.accent}`}
              >
                {Content}
              </div>
            );
          })}
        </div>
        {ingredientsTop.length > 0 && (
          <section className="w-full max-w-4xl rounded-[32px] border border-[#E7C9A1] bg-white/90 p-6 shadow-inner">
            <div className="flex items-center justify-between text-sm font-semibold text-[#6B2E00]/80">
              <span>가장 많이 사용한 재료 TOP3</span>
              <span className="text-xs text-[#6B2E00]/60">이번 달 진행완료 기준</span>
            </div>
            <div className="mt-4 flex flex-col gap-6 sm:flex-row sm:items-center">
              <div className="mx-auto relative">
                <svg width="220" height="220" viewBox="0 0 160 160">
                  <circle cx="80" cy="80" r="55" fill="#ffffff" stroke="none" />
                  <circle cx="80" cy="80" r="18" fill="#fff" stroke="none" />
                  {(() => {
                    const radius = 55;
                    const circumference = 2 * Math.PI * radius;
                    const total = ingredientsTop.reduce((sum, entry) => sum + entry.count, 0);
                    let offset = 0;
                    return ingredientsTop.slice(0, 3).map((item, index) => {
                      const value = total > 0 ? item.count / total : 0;
                      const dash = value * circumference;
                      const color = DONUT_COLORS[index % DONUT_COLORS.length];
                      const arc = (
                        <circle
                          key={`${item.name}-${index}`}
                          cx="80"
                          cy="80"
                          r={radius}
                          fill="transparent"
                          stroke={color}
                          strokeWidth="30"
                          strokeDasharray={`${dash} ${circumference - dash}`}
                          strokeDashoffset={-offset}
                        />
                      );
                      const midOffset = offset + dash / 2;
                      const angle = midOffset / radius;
                      const textX = 80 + Math.cos(angle) * 40;
                      const textY = 80 + Math.sin(angle) * 40;
                      offset += dash;
                      return (
                        <g key={`${item.name}-segment`}>
                          {arc}
                          <text
                            x={textX}
                            y={textY}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize="11"
                            fill="#ffffff"
                            fontWeight="600"
                          >
                            {Math.round(value * 100)}%
                          </text>
                        </g>
                      );
                    });
                  })()}
                </svg>
                <div className="absolute inset-0 flex items-center justify-center text-xs text-[#6B2E00]/70 font-semibold">
                  TOP3
                </div>
              </div>
              <ul className="space-y-2 text-sm text-[#6B2E00] sm:w-1/2">
                {ingredientsTop.map((item, index) => {
                  const total = ingredientsTop.reduce((sum, entry) => sum + entry.count, 0);
                  const percentage = total > 0 ? ((item.count / total) * 100).toFixed(1) : "0.0";
                  return (
                    <li key={`${item.name}-${index}`} className="flex items-center justify-between rounded-2xl bg-[#FDF4E3] px-4 py-2 shadow-sm">
                      <span className="flex items-center gap-2 font-medium">
                        <span
                          className="inline-block h-3 w-3 rounded-full"
                          style={{ backgroundColor: DONUT_COLORS[index % DONUT_COLORS.length] }}
                        />
                        {item.name}
                      </span>
                      <span className="text-xs text-[#6B2E00]/70">{percentage}%</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
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
