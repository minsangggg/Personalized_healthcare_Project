import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { useAuth } from "./AuthContext";
import { FaUserCircle } from "react-icons/fa";

type EventItem = {
  event_id: number;
  event_name: string;
  event_description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
};

export default function EventsPage() {
  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const UserCircleIcon = FaUserCircle as React.ComponentType<{ className?: string }>;
  const navigate = useNavigate();
  const [showQuickMenu, setShowQuickMenu] = useState(false);
  const [quickMenuPos, setQuickMenuPos] = useState<{ top: number; left: number }>({ top: 12, left: 12 });
  const quickMenuButtonRef = useRef<HTMLButtonElement | null>(null);

  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvents = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch<{ events: EventItem[] }>("/events");
        setEvents(data.events || []);
      } catch (err) {
        const message = err instanceof Error ? err.message : "이벤트를 불러오지 못했습니다.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, []);

  const handleUpload = async (eventId: number, file: File) => {
    if (!userId) {
      alert("로그인 후 업로드할 수 있습니다.");
      return;
    }
    setUploadingId(eventId);
    setUploadMessage(null);
    try {
      const form = new FormData();
      form.append("user_id", userId);
      form.append("file", file);
      await apiFetch(`/events/${eventId}/upload`, {
        method: "POST",
        body: form,
      });
      setUploadMessage("업로드가 완료되었습니다.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "업로드에 실패했습니다.";
      setUploadMessage(message);
    } finally {
      setUploadingId(null);
    }
  };

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
          <h2 className="text-lg font-extrabold">이벤트 / 대회</h2>
          <p className="mt-2 text-sm text-[#6B2E00]/80">일정 · 참가 · 결과 확인 메뉴입니다.</p>
        </div>

        {loading && (
          <div className="rounded-2xl bg-white/85 p-4 shadow text-sm text-[#6B2E00]/70">불러오는 중...</div>
        )}
        {error && <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-600 shadow">{error}</div>}
        {!loading && !error && (
          <div className="grid grid-cols-1 gap-3">
            {events.length === 0 ? (
              <div className="rounded-2xl bg-white/85 p-4 shadow text-sm text-[#6B2E00]/70">
                현재 표시할 이벤트가 없습니다.
              </div>
            ) : (
              events.map((item) => (
                <div key={item.event_id} className="rounded-2xl bg-white/90 p-4 shadow">
                  <p className="text-xs font-semibold text-[#8B4000]">ID: {item.event_id}</p>
                  <h3 className="mt-1 text-lg font-bold">{item.event_name}</h3>
                {item.event_description && (
                  <p className="mt-1 text-sm text-[#6B2E00]/80 whitespace-pre-line">{item.event_description}</p>
                )}
                  <p className="mt-2 text-xs text-[#6B2E00]/70">
                    {item.start_date || "?"} ~ {item.end_date || "?"}
                  </p>
                  <div className="mt-3">
                    <label className="block text-xs font-semibold text-[#6B2E00]/80 mb-1">
                      대회 사진 업로드
                    </label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleUpload(item.event_id, file);
                          e.target.value = "";
                        }
                      }}
                      className="w-full text-sm text-[#6B2E00]"
                    />
                    {uploadingId === item.event_id && (
                      <p className="mt-1 text-xs text-[#6B2E00]/70">업로드 중...</p>
                    )}
                    {uploadMessage && (
                      <p className="mt-1 text-xs text-[#8B4000]">{uploadMessage}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </VideoBackgroundLayout>
  );
}
