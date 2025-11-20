import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "./AuthContext";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { FaUserCircle } from "react-icons/fa";

type ProgressSummary = {
  user_id: string;
  total_posts: number;
  likes_received: number;
  likes_given: number;
  rewards: number;
  last_goal: number;
  goal_updated_at?: string | null;
};

export default function ProgressPage() {
  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const UserCircleIcon = FaUserCircle as React.ComponentType<{ className?: string }>;
  const navigate = useNavigate();
  const [showQuickMenu, setShowQuickMenu] = useState(false);
  const [quickMenuPos, setQuickMenuPos] = useState<{ top: number; left: number }>({ top: 12, left: 12 });
  const quickMenuButtonRef = useRef<HTMLButtonElement | null>(null);
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setError("로그인 후 이용 가능합니다.");
      return;
    }
    const fetchProgress = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch<ProgressSummary>(`/progress/${userId}`);
        setSummary(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "진행 정보를 불러오지 못했습니다.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    fetchProgress();
  }, [userId]);

  return (
    <VideoBackgroundLayout contentClassName="text-[#6B2E00]" showHomeButton={false}>
      <header className="relative pt-6 pb-4 text-center">
        <button
          type="button"
          aria-label="메뉴"
          ref={quickMenuButtonRef}
          onClick={() => {
            const rect = quickMenuButtonRef.current?.getBoundingClientRect();
            if (rect) {
              setQuickMenuPos({ top: rect.top, left: rect.left });
            }
            setShowQuickMenu(true);
          }}
          className="absolute left-6 top-3 flex h-9 w-9 flex-col items-center justify-center gap-[6px] rounded-full bg-[#6B2E00] text-white shadow hover:bg-[#4c2100]"
        >
          <span className="block h-[2px] w-5 bg-white/80" />
          <span className="block h-[2px] w-5 bg-white/80" />
          <span className="block h-[2px] w-5 bg-white/80" />
        </button>
        <h1 className="text-xl font-extrabold tracking-wide">CookUS</h1>
        <nav className="mt-3 flex items-center justify-center gap-5 text-sm font-semibold">
          <Link to="/" className="hover:text-[#8B4000]">
            냉장고
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
          {user ? (
            <button onClick={logout} className="hover:text-[#8B4000]">
              로그아웃
            </button>
          ) : (
            <Link to="/login" className="hover:text-[#8B4000]">
              로그인
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

      {showQuickMenu && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-black/25"
            aria-label="오버레이 닫기"
            onClick={() => setShowQuickMenu(false)}
          />
          <div
            className="absolute w-[280px] max-w-[85%] rounded-2xl bg-[#FFF2D9] p-6 text-[#6B2E00] shadow-2xl animate-slide-in-left"
            style={{ top: `${quickMenuPos.top}px`, left: `${quickMenuPos.left}px` }}
          >
            <button
              type="button"
              onClick={() => setShowQuickMenu(false)}
              className="absolute right-5 top-4 text-xl font-bold text-[#6B2E00]"
              aria-label="닫기"
            >
              &times;
            </button>
            <h3 className="text-lg font-extrabold">바로가기</h3>
            <p className="mt-1 text-sm text-[#6B2E00]/80">이벤트· 게시판· 나의 진행을 빠르게 확인하세요.</p>

            <div className="mt-5 space-y-3">
              <button
                type="button"
                onClick={() => {
                  setShowQuickMenu(false);
                  navigate("/events");
                }}
                className="w-full rounded-2xl bg-[#F7D98A]/90 px-4 py-3 text-left text-sm font-semibold shadow hover:bg-[#f1d082]"
              >
                이벤트/ 대회
                <span className="mt-1 block text-xs font-medium text-[#6B2E00]/80">
                  일정 · 참가 · 결과 확인 메뉴로 이동
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowQuickMenu(false);
                  navigate("/board");
                }}
                className="w-full rounded-2xl bg-[#FFB15E] px-4 py-3 text-left text-sm font-semibold text-white shadow hover:bg-[#ff9d3d]"
              >
                게시판
                <span className="mt-1 block text-xs font-medium text-white/90">
                  글 작성 · 좋아요· 인기글 모아보기
                </span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowQuickMenu(false);
                  navigate("/progress");
                }}
                className="w-full rounded-2xl border border-[#E7C9A1] bg-white px-4 py-3 text-left text-sm font-semibold text-[#6B2E00] shadow"
              >
                나의 진행
                <span className="mt-1 block text-xs font-medium text-[#6B2E00]/80">
                  목표 진행도· 보상 캐시 확인
                </span>
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 px-6 pb-8 flex flex-col gap-4">
        <div className="rounded-3xl bg-white/85 p-5 text-sm text-[#6B2E00] shadow-inner backdrop-blur">
          <h2 className="text-lg font-extrabold">나의 진행</h2>
          <p className="mt-2 text-sm text-[#6B2E00]/80">목표 진행도 · 보상 캐시 확인 메뉴입니다.</p>
        </div>

        {loading && (
          <div className="rounded-2xl bg-white/85 p-4 shadow text-sm text-[#6B2E00]/70">불러오는 중...</div>
        )}
        {error && <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-600 shadow">{error}</div>}
        {!loading && !error && summary && (
          <div className="rounded-2xl bg-white/90 p-4 shadow space-y-2 text-sm">
            <p className="font-bold text-[#8B4000]">사용자: {summary.user_id}</p>
            <p>작성한 게시글: {summary.total_posts}개</p>
            <p>받은 좋아요: {summary.likes_received}개</p>
            <p>남긴 좋아요: {summary.likes_given}개</p>
            <p>보상 캐시 적용: {summary.rewards}건</p>
            <p>최근 목표: {summary.last_goal}</p>
            <p className="text-xs text-[#6B2E00]/70">업데이트: {summary.goal_updated_at || "-"}</p>
          </div>
        )}
        {!loading && !error && !summary && (
          <div className="rounded-2xl bg-white/85 p-4 shadow text-sm text-[#6B2E00]/70">
            현재 표시할 데이터가 없습니다.
          </div>
        )}
      </main>
    </VideoBackgroundLayout>
  );
}
