import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { useAuth } from "./AuthContext";
import { FaUserCircle } from "react-icons/fa";

type PostItem = {
  content_id: number;
  event_id?: number | null;
  user_id: string;
  content_title: string;
  content_text: string;
  img_url?: string | null;
  like_count: number;
  created_at?: string | null;
};

export default function BoardPage() {
  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const UserCircleIcon = FaUserCircle as React.ComponentType<{ className?: string }>;
  const navigate = useNavigate();
  const [showQuickMenu, setShowQuickMenu] = useState(false);
  const [quickMenuPos, setQuickMenuPos] = useState<{ top: number; left: number }>({ top: 12, left: 12 });
  const quickMenuButtonRef = useRef<HTMLButtonElement | null>(null);

  const [posts, setPosts] = useState<PostItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const [uploadMessage, setUploadMessage] = useState<Record<number, string | null>>({});
  const [showForm, setShowForm] = useState(false);
  const [newEventId, setNewEventId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newText, setNewText] = useState("");
  const [createMessage, setCreateMessage] = useState<string | null>(null);
  const [newImage, setNewImage] = useState<File | null>(null);

  useEffect(() => {
    const fetchPosts = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch<{ posts: PostItem[] }>("/board");
        setPosts(data.posts || []);
      } catch (err) {
        const message = err instanceof Error ? err.message : "게시판을 불러오지 못했습니다.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };
    fetchPosts();
  }, []);

  const handleUpload = async (contentId: number, file: File) => {
    if (!userId) {
      alert("로그인 후 업로드할 수 있습니다.");
      return;
    }
    setUploadingId(contentId);
    setUploadMessage((prev) => ({ ...prev, [contentId]: null }));
    try {
      const form = new FormData();
      form.append("user_id", userId);
      form.append("content_id", String(contentId));
      form.append("file", file);
      const data = await apiFetch<{ img_url?: string }>(`/board/${contentId}/upload`, {
        method: "POST",
        body: form,
      });
      setUploadMessage((prev) => ({ ...prev, [contentId]: "업로드가 완료되었습니다." }));
      if (data.img_url) {
        setPosts((prev) =>
          prev.map((post) =>
            post.content_id === contentId ? { ...post, img_url: data.img_url } : post
          )
        );
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "업로드에 실패했습니다.";
      setUploadMessage((prev) => ({ ...prev, [contentId]: message }));
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
        <div className="rounded-3xl bg-[#FFF2D9] border border-[#E7C9A1] p-5 text-sm text-[#6B2E00] shadow-inner flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold">게시판</h2>
            <p className="mt-2 text-sm text-[#6B2E00]/80">글 작성 · 좋아요 · 인기글 확인 메뉴입니다.</p>
          </div>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="rounded-full bg-[#F2994A] px-4 py-2 text-xs font-semibold text-white shadow hover:bg-[#f08a29]"
          >
            작성
          </button>
        </div>
        {!showForm ? null : (
          <form
            className="rounded-3xl bg-white/90 p-5 text-sm text-[#6B2E00] shadow space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (!userId) {
                alert("로그인 후 작성할 수 있습니다.");
                return;
              }
              if (!newEventId.trim() || !newTitle.trim() || !newText.trim()) {
                setCreateMessage("모든 필드를 입력해주세요.");
                return;
              }
              (async () => {
                try {
                const created = await apiFetch<PostItem>("/board", {
                  method: "POST",
                  body: JSON.stringify({
                    event_id: Number(newEventId),
                    id: userId,
                    content_title: newTitle,
                    content_text: newText,
                  }),
                });
                setPosts((prev) => [created, ...prev]);
                setNewEventId("");
                setNewTitle("");
                setNewText("");
                if (newImage) {
                  await handleUpload(created.content_id, newImage);
                  setNewImage(null);
                }
                setCreateMessage("작성되었습니다.");
                } catch (err) {
                  const message =
                    err instanceof Error ? err.message : "작성에 실패했습니다.";
                  setCreateMessage(message);
                }
              })().catch((error) => {
                console.error("Create post failed:", error);
              });
            }}
          >
            <div>
              <label className="block text-xs font-semibold text-[#6B2E00]/80 mb-1">
                이벤트 ID
              </label>
              <input
                type="number"
                value={newEventId}
                onChange={(e) => setNewEventId(e.target.value)}
                className="w-full rounded-xl border border-[#D7B78A] px-3 py-2"
                placeholder="이벤트 ID를 입력하세요"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6B2E00]/80 mb-1">
                제목
              </label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full rounded-xl border border-[#D7B78A] px-3 py-2"
                placeholder="제목을 입력하세요"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6B2E00]/80 mb-1">
                내용
              </label>
              <textarea
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-[#D7B78A] px-3 py-2"
                placeholder="내용을 입력하세요"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6B2E00]/80 mb-1">
                이미지 첨부(선택)
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setNewImage(e.target.files?.[0] ?? null)}
                className="w-full text-sm text-[#6B2E00]"
              />
            </div>
            {createMessage && (
              <p className="text-xs text-[#8B4000]">{createMessage}</p>
            )}
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setNewEventId("");
                  setNewTitle("");
                  setNewText("");
                  setNewImage(null);
                  setCreateMessage(null);
                }}
                className="rounded-xl border border-[#D7B78A] px-4 py-2 text-sm font-semibold text-[#6B2E00] hover:bg-[#F7D98A]/40"
              >
                취소
              </button>
              <button
                type="submit"
                className="rounded-xl bg-[#F2994A] px-4 py-2 text-sm font-semibold text-white shadow hover:bg-[#f08a29]"
              >
                등록
              </button>
            </div>
          </form>
        )}

        {loading && (
          <div className="rounded-2xl bg-white/85 p-4 shadow text-sm text-[#6B2E00]/70">불러오는 중...</div>
        )}
        {error && <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-600 shadow">{error}</div>}
        {!loading && !error && (
          <div className="space-y-3">
            {posts.length === 0 ? (
              <div className="rounded-2xl bg-white/85 p-4 shadow text-sm text-[#6B2E00]/70">
                현재 게시물이 없습니다.
              </div>
            ) : (
              posts.map((post) => (
                <div key={post.content_id} className="rounded-2xl bg-white/90 p-4 shadow">
                  <h3 className="mt-1 text-lg font-bold">{post.content_title}</h3>
                  <p className="mt-1 text-sm whitespace-pre-line text-[#6B2E00]/90">{post.content_text}</p>
                  <p className="mt-2 text-xs text-[#6B2E00]/70">작성자: {post.user_id}</p>
                  <p className="mt-1 text-xs text-[#6B2E00]/70">
                    좋아요 {post.like_count} · {post.created_at || ""}
                  </p>
                  {post.img_url && (
                    <div className="mt-3">
                      <img
                        src={post.img_url}
                        alt={`${post.content_title} 이미지`}
                        className="w-full rounded-xl object-cover"
                      />
                    </div>
                  )}
                  <div className="mt-3">
                    <label className="block text-xs font-semibold text-[#6B2E00]/80 mb-1">
                      사진 업로드
                    </label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleUpload(post.content_id, file);
                          e.target.value = "";
                        }
                      }}
                      className="w-full text-sm text-[#6B2E00]"
                    />
                    {uploadingId === post.content_id && (
                      <p className="mt-1 text-xs text-[#6B2E00]/70">업로드 중...</p>
                    )}
                    {uploadMessage[post.content_id] && (
                      <p className="mt-1 text-xs text-[#8B4000]">{uploadMessage[post.content_id]}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </main>

      <footer className="rounded-3xl bg-[#F6E8C9]/90 px-6 py-6 text-center text-xs text-[#6B2E00] shadow-inner mt-auto">
        <p className="text-sm font-semibold">2025 Recipe Market</p>
        <p className="mt-3 flex justify-center gap-4 font-medium">
          <span>소개</span>
          <span>FAQ</span>
        </p>
        <p className="mt-3">Recipe Market | 123-45-6789 | +82-1234-4567</p>
        <p>hello@recipemarket.com</p>
        <p className="mt-2">이용약관 | 개인정보처리방침</p>
      </footer>
    </VideoBackgroundLayout>
  );
}
