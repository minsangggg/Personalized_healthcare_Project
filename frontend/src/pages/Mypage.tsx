import React, { useEffect, useMemo, useState, type ComponentType } from "react";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

import { useAuth } from "./AuthContext";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";

type UserInfo = {
  id: string;
  user_name: string;
  email: string;
  gender: string;
  date_of_birth: string;
  goal?: string;
  cooking_level?: string;
};

const TEXT = {
  nav: {
    fridge: "\uB0C9\uC7A5\uACE0",
    calendar: "\uCE98\uB9B0\uB354",
    dashboard: "\uB300\uC2DC\uBCF4\uB4DC",
    logout: "\uB85C\uADF8\uC544\uC6C3",
    login: "\uB85C\uADF8\uC778",
    myPage: "\uB9C8\uC774\uD398\uC774\uC9C0",
  },
  sectionTitle: "\uB0B4 \uC815\uBCF4",
  labels: {
    email: "\uC774\uBA54\uC77C",
    gender: "\uC131\uBCC4",
    birth: "\uC0DD\uB144\uC6D4\uC77C",
    goal: "\uC8FC\uAC04 \uBAA9\uD45C",
    level: "\uC694\uB9AC \uB808\uBCA8",
  },
  selectPlaceholder: "\uB808\uBCA8\uC744 \uC120\uD0DD\uD558\uC138\uC694",
  buttons: {
    save: "\uC815\uBCF4 \uC800\uC7A5",
    delete: "\uD68C\uC6D0 \uD0C8\uD1F4",
  },
  alerts: {
    requireLogin: "\uB85C\uADF8\uC778 \uD6C4 \uC774\uC6A9\uD574 \uC8FC\uC138\uC694.",
    saveSuccess: "\uC815\uBCF4\uAC00 \uC800\uC7A5\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
    saveFail: "\uC815\uBCF4\uB97C \uC800\uC7A5\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
    deleteConfirm: "\uC815\uB9D0 \uD68C\uC6D0 \uD0C8\uD1F4\uB97C \uC9C4\uD589\uD558\uC2DC\uACA0\uC5B4\uC694?",
    deleteSuccess: "\uD68C\uC6D0 \uD0C8\uD1F4\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.",
    deleteFail: "\uD68C\uC6D0 \uD0C8\uD1F4\uB97C \uC644\uB8CC\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
  },
  footer: {
    title: "2025 Recipe Market",
    about: "\uC18C\uAC1C",
    notice: "\uACF5\uC9C0\uC0AC\uD56D",
    faq: "FAQ",
    contact: "Recipe Market | 123-45-6789 | +82-1234-4567",
    email: "hello@recipemarket.com",
    policy: "\uC774\uC6A9\uC57D\uAD00 | \uAC1C\uC778\uC815\uBCF4\uCC98\uB9AC\uBC29\uCE68",
  },
  placeholders: {
    goal: "",
  },
  loading: "\uD68C\uC6D0 \uC815\uBCF4\uB97C \uBD88\uB7EC\uC624\uB294 \uC911...",
  processing: "\uCC98\uB9AC \uC911\uC785\uB2C8\uB2E4...",
};

const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;

export default function MyPage() {
  const { user, logout } = useAuth();
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("");
  const [loading, setLoading] = useState(false);

  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);
  const headerName = useMemo(
    () =>
      userInfo?.user_name ??
      user?.name ??
      localStorage.getItem("currentUserName") ??
      TEXT.nav.myPage,
    [userInfo?.user_name, user?.name]
  );

  useEffect(() => {
    const loadUserInfo = async () => {
      if (!userId) return;
      try {
        const data = await apiFetch<UserInfo>(`/get_user_info/${userId}`);
        setUserInfo(data);
        setGoal(data.goal ?? "");
        setLevel(data.cooking_level ?? "");
        if (data.user_name) {
          localStorage.setItem("currentUserName", data.user_name);
        }
      } catch (error) {
        console.error("Failed to load user info:", error);
      }
    };

    loadUserInfo();
  }, [userId]);

  const handleUpdate = async () => {
    if (!userId) {
      alert(TEXT.alerts.requireLogin);
      return;
    }

    setLoading(true);
    try {
      await apiFetch("/update_profile", {
        method: "PUT",
        body: JSON.stringify({
          id: userId,
          goal,
          cooking_level: level,
        }),
      });
      alert(TEXT.alerts.saveSuccess);
    } catch (error) {
      console.error("Failed to update profile:", error);
      alert(TEXT.alerts.saveFail);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!userId) {
      alert(TEXT.alerts.requireLogin);
      return;
    }

    const confirmDelete = window.confirm(TEXT.alerts.deleteConfirm);
    if (!confirmDelete) return;

    setLoading(true);
    try {
      const data = await apiFetch<{ message?: string }>(`/delete_user/${userId}`, {
        method: "DELETE",
      });
      alert(data.message ?? TEXT.alerts.deleteSuccess);
      logout();
      localStorage.clear();
      sessionStorage.setItem("skipSplash", "true");
      window.location.href = "/";
    } catch (error) {
      console.error("Failed to delete account:", error);
      alert(TEXT.alerts.deleteFail);
    } finally {
      setLoading(false);
    }
  };

  if (!userInfo) {
    return (
      <VideoBackgroundLayout
        contentClassName="text-[#6B2E00] flex items-center justify-center px-6"
        showVideo
      >
        <p className="rounded-2xl bg-[#6B2E00]/70 px-6 py-3 text-sm font-semibold text-white shadow">
          {TEXT.loading}
        </p>
      </VideoBackgroundLayout>
    );
  }

  return (
    <>
      <VideoBackgroundLayout contentClassName="text-[#6B2E00]">
        <header className="relative bg-transparent text-center pt-4 pb-2 sticky top-0 z-50">
          <h1 className="text-xl font-extrabold">CookUS </h1>
          <nav className="mt-2 flex justify-center gap-6 text-sm font-medium">
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
          <div className="mt-3 text-center text-white drop-shadow-[0_4px_8px_rgba(0,0,0,0.35)]">
            <p className="text-2xl font-extrabold tracking-tight">{TEXT.sectionTitle}</p>
            <p className="mt-1 text-sm font-medium text-white/80">
              {userInfo.user_name}님만의 정보를 관리해 보세요.
            </p>
          </div>

          <div className="mt-6 bg-white/85 rounded-3xl shadow-inner border border-[#E2B857]/60 p-6 backdrop-blur space-y-4">
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-sm font-semibold mb-1">{TEXT.labels.email}</label>
                <input
                  type="text"
                  value={userInfo.email}
                  readOnly
                  className="w-full rounded-lg border border-[#D7B78A] bg-[#FFFDF6] px-3 py-2 text-sm text-[#6B2E00]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold mb-1">{TEXT.labels.gender}</label>
                  <input
                    type="text"
                    value={userInfo.gender}
                    readOnly
                    className="w-full rounded-lg border border-[#D7B78A] bg-[#FFFDF6] px-3 py-2 text-sm text-[#6B2E00]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold mb-1">{TEXT.labels.birth}</label>
                  <input
                    type="text"
                    value={userInfo.date_of_birth}
                    readOnly
                    className="w-full rounded-lg border border-[#D7B78A] bg-[#FFFDF6] px-3 py-2 text-sm text-[#6B2E00]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold mb-1">{TEXT.labels.goal}</label>
                <input
                  type="text"
                  value={goal}
                  onChange={(event) => setGoal(event.target.value)}
                  placeholder={TEXT.placeholders.goal}
                  className="w-full rounded-lg border border-[#D7B78A] bg-white px-3 py-2 text-sm text-[#6B2E00]"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-1">{TEXT.labels.level}</label>
                <select
                  value={level}
                  onChange={(event) => setLevel(event.target.value)}
                  className="w-full rounded-lg border border-[#D7B78A] bg-white px-3 py-2 text-sm text-[#6B2E00]"
                >
                  <option value="">{TEXT.selectPlaceholder}</option>
                  <option value="상">상</option>
                  <option value="하">하</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                type="button"
                onClick={handleUpdate}
                className="rounded-xl bg-[#F2994A] py-2 text-white font-semibold shadow hover:bg-[#f08a29] transition disabled:opacity-60"
                disabled={loading}
              >
                {TEXT.buttons.save}
              </button>

              <button
                type="button"
                onClick={handleDeleteAccount}
                className="rounded-xl bg-[#ff6767] py-2 text-white font-semibold shadow hover:bg-[#e64a4a] transition disabled:opacity-60"
                disabled={loading}
              >
                {TEXT.buttons.delete}
              </button>
            </div>
          </div>

          <div className="mt-auto space-y-6 pb-2">
            <footer className="rounded-3xl bg-[#F6E8C9]/90 px-6 py-6 text-center text-xs text-[#6B2E00] shadow-inner">
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
          </div>
        </main>
      </VideoBackgroundLayout>

      {loading && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <p className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-[#6B2E00] shadow">
            {TEXT.processing}
          </p>
        </div>
      )}
    </>
  );
}
