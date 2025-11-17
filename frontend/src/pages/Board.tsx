import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";
import { useAuth } from "./AuthContext";
import { FaUserCircle, FaBars } from "react-icons/fa";

type PostItem = {
  content_id: number;
  event_id?: number | null;
  user_id: string;
  content_title: string;
  content_text: string;
  like_count: number;
  created_at?: string | null;
};

export default function BoardPage() {
  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const UserCircleIcon = FaUserCircle as React.ComponentType<{ className?: string }>;
  const BarsIcon = FaBars as React.ComponentType<{ className?: string }>;

  const [posts, setPosts] = useState<PostItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <VideoBackgroundLayout contentClassName="text-[#6B2E00]" showHomeButton={false}>
      <header className="relative pt-6 pb-4 text-center">
        <Link
          to="/"
          className="absolute left-6 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white/70 text-[#6B2E00] shadow hover:bg-white"
        >
          <BarsIcon className="h-5 w-5" />
        </Link>
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

      <main className="flex-1 px-6 pb-8 flex flex-col gap-4">
        <div className="rounded-3xl bg-white/85 p-5 text-sm text-[#6B2E00] shadow-inner backdrop-blur">
          <h2 className="text-lg font-extrabold">게시판</h2>
          <p className="mt-2 text-sm text-[#6B2E00]/80">글 작성 · 좋아요 · 인기글 확인 메뉴입니다.</p>
        </div>

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
                  <p className="text-xs font-semibold text-[#8B4000]">
                    ID: {post.content_id} {post.event_id ? `· EVENT ${post.event_id}` : ""}
                  </p>
                  <h3 className="mt-1 text-lg font-bold">{post.content_title}</h3>
                  <p className="mt-1 text-sm whitespace-pre-line text-[#6B2E00]/90">{post.content_text}</p>
                  <p className="mt-2 text-xs text-[#6B2E00]/70">작성자: {post.user_id}</p>
                  <p className="mt-1 text-xs text-[#6B2E00]/70">
                    좋아요 {post.like_count} · {post.created_at || ""}
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </VideoBackgroundLayout>
  );
}
