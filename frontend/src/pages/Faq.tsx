import React, { useEffect, useMemo, useState, type ComponentType } from "react";
import { Link } from "react-router-dom";
import { FaUserCircle, FaSearch } from "react-icons/fa";

import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { apiFetch } from "../api/client";
import { useAuth } from "./AuthContext";

type FaqRecord = {
  faq_id: number;
  question: string;
  answer: string;
  category?: string | null;
  created_at?: string | null;
};

const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;
const SearchIcon = FaSearch as ComponentType<{ className?: string }>;

const TEXT = {
  nav: {
    fridge: "냉장고",
    calendar: "캘린더",
    dashboard: "대시보드",
    logout: "로그아웃",
    login: "로그인",
  },
  tagline: {
    line1: "냉장고 속 재료로",
    line2: "레시피를 추천받아요.",
  },
  faqHeading: {
    title: "자주 묻는 질문",
    subtitle: "궁금한 점을 빠르게 확인하세요.",
  },
  searchPlaceholder: "궁금한 것을 검색해보세요.",
  empty: "등록된 FAQ가 없습니다.",
  noResult: "검색과 일치하는 FAQ가 없습니다.",
  error: "FAQ를 불러오지 못했습니다.",
  loading: "불러오는 중...",
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

const formatDate = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
    .format(date)
    .replace(/\.$/, "");
};

export default function FaqPage() {
  const { user, logout } = useAuth();
  const [items, setItems] = useState<FaqRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 6;

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<FaqRecord[]>("/faq")
      .then((data) => {
        if (Array.isArray(data)) {
          setItems(
            data.map((item) => ({
              ...item,
              question: item.question?.trim() ?? "",
              answer: item.answer?.trim() ?? "",
              category: item.category ?? null,
            }))
          );
        } else {
          setItems([]);
        }
      })
      .catch((err) => {
        setError(err?.message || TEXT.error);
        setItems([]);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const filteredItems = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();
    if (!normalized) {
      return items;
    }
    return items.filter((item) => {
      const haystack = `${item.question} ${item.answer} ${item.category ?? ""}`.toLowerCase();
      return haystack.includes(normalized);
    });
  }, [items, searchTerm]);

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / ITEMS_PER_PAGE));

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, items.length]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const pagedItems = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredItems.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredItems, currentPage, ITEMS_PER_PAGE]);

  const groupedFaqs = useMemo(() => {
    if (!pagedItems.length) {
      return [];
    }
    const map = new Map<string, FaqRecord[]>();
    pagedItems.forEach((item) => {
      const key = (item.category?.trim() || "기타").toUpperCase();
      if (!map.has(key)) {
        map.set(key, []);
      }
      map.get(key)?.push(item);
    });
    return Array.from(map.entries()).map(([category, records]) => ({
      category,
      records,
    }));
  }, [pagedItems]);

  const handlePageChange = (page: number) => {
    if (page < 1 || page > totalPages || page === currentPage) {
      return;
    }
    setCurrentPage(page);
  };

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

      <main className="flex-1 px-6 pb-8 flex flex-col">
        <div className="text-center text-white drop-shadow-[0_4px_8px_rgba(0,0,0,0.35)]">
          <p className="text-2xl font-extrabold tracking-tight">{TEXT.tagline.line1}</p>
          <p className="text-2xl font-extrabold tracking-tight">{TEXT.tagline.line2}</p>
        </div>

        <section className="mt-6 flex-1 overflow-hidden flex flex-col">
          <div className="text-center text-[#6B2E00]">
            <p className="text-xl font-extrabold tracking-tight">{TEXT.faqHeading.title}</p>
            <p className="text-sm font-semibold tracking-tight">{TEXT.faqHeading.subtitle}</p>
          </div>
          <div className="my-4 h-px bg-gradient-to-r from-transparent via-[#E7C9A1] to-transparent" />
          <div className="relative mb-4">
            <SearchIcon className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#B2702D]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={TEXT.searchPlaceholder}
              className="w-full rounded-2xl border border-[#E7C9A1] bg-white/70 py-3 pl-10 pr-4 text-sm placeholder:text-[#B2702D]/60 focus:border-[#B2702D] focus:outline-none"
            />
          </div>
          <div className="flex-1 overflow-y-auto pr-1">
            {loading ? (
              <p className="text-center text-sm font-semibold">{TEXT.loading}</p>
            ) : error ? (
              <p className="text-center text-sm font-semibold text-red-600">{error}</p>
            ) : items.length === 0 ? (
              <p className="text-center text-sm font-semibold text-[#6B2E00]/80">{TEXT.empty}</p>
            ) : filteredItems.length === 0 ? (
              <p className="text-center text-sm font-semibold text-[#6B2E00]/80">{TEXT.noResult}</p>
            ) : (
              groupedFaqs.map(({ category, records }) => (
                <div key={category} className="mb-5 last:mb-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-[#B2702D]">
                    {category}
                  </p>
                  <div className="mt-2 space-y-3">
                    {records.map((item) => (
                      <article
                        key={item.faq_id}
                        className="rounded-2xl border border-[#E7C9A1] bg-white/90 px-4 py-3 text-sm shadow"
                      >
                        <h3 className="text-base font-bold">{item.question}</h3>
                        <p className="mt-2 whitespace-pre-line leading-relaxed">{item.answer}</p>
                        {formatDate(item.created_at) && (
                          <p className="mt-3 text-right text-[11px] text-[#B2702D]">
                            {formatDate(item.created_at)}
                          </p>
                        )}
                      </article>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
          {filteredItems.length > 0 && totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm font-semibold text-[#6B2E00]">
              <button
                type="button"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className={`h-8 w-8 rounded-full border border-[#E7C9A1] text-center ${
                  currentPage === 1 ? "opacity-40" : "hover:bg-[#F6E8C9]"
                }`}
              >
                ‹
              </button>
              {Array.from({ length: totalPages }).map((_, index) => {
                const page = index + 1;
                const isActive = page === currentPage;
                return (
                  <button
                    key={page}
                    type="button"
                    onClick={() => handlePageChange(page)}
                    className={`h-8 w-8 rounded-full text-center ${
                      isActive
                        ? "bg-[#E7C9A1] text-[#6B2E00]"
                        : "text-[#6B2E00]/70 hover:bg-[#F6E8C9]"
                    }`}
                  >
                    {page}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className={`h-8 w-8 rounded-full border border-[#E7C9A1] text-center ${
                  currentPage === totalPages ? "opacity-40" : "hover:bg-[#F6E8C9]"
                }`}
              >
                ›
              </button>
            </div>
          )}
        </section>

        <footer className="mt-6 rounded-3xl bg-[#F6E8C9]/90 px-6 py-6 text-center text-xs text-[#6B2E00] shadow-inner">
          <p className="text-sm font-semibold">{TEXT.footer.title}</p>
          <p className="mt-3 flex justify-center gap-4 font-medium">
            <span>{TEXT.footer.about}</span>
            <span className="font-bold underline underline-offset-4">{TEXT.footer.faq}</span>
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
