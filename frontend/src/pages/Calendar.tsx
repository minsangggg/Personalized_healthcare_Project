import React, { useEffect, useMemo, useState, type ComponentType } from "react";
import Calendar from "react-calendar";
import "react-calendar/dist/Calendar.css";
import { Link } from "react-router-dom";
import { FaUserCircle, FaCalendarDay, FaUtensils } from "react-icons/fa";

import { useAuth } from "./AuthContext";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";

type StoredRecipe = {
  recipe_nm_ko?: string;
  selected_date?: string;
  level_nm?: string;
  cooking_time?: string;
  step_text?: string;
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
  title: "\uC694\uB9AC \uCE98\uB9B0\uB354",
  selectedDatePrefix: "\uC120\uD0DD\uD55C \uB0A0\uC9DC:",
  noRecipes: "\uD574\uB2F9 \uB0A0\uC9DC\uC5D0 \uC800\uC7A5\uB41C \uB808\uC2DC\uD53C\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
  level: "\uB09C\uC774\uB3C4",
  cookingTime: "\uC870\uB9AC\uC2DC\uAC04",
  detailButton: "\uC0C1\uC138 \uBCF4\uAE30",
  footer: {
    title: "2025 Recipe Market",
    about: "\uC18C\uAC1C",
    notice: "\uACF5\uC9C0\uC0AC\uD56D",
    faq: "FAQ",
    contact: "Recipe Market | 123-45-6789 | +82-1234-4567",
    email: "hello@recipemarket.com",
    policy: "\uC774\uC6A9\uC57D\uAD00 | \uAC1C\uC778\uC815\uBCF4\uCC98\uB9AC\uBC29\uCE68",
  },
  modal: {
    defaultName: "\uB808\uC2DC\uD53C",
    steps: "\uC870\uB9AC \uC21C\uC11C:",
    close: "\uB2EB\uAE30",
    noInfo: "\uC870\uB9AC \uC21C\uC11C \uC815\uBCF4\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
  },
};

export default function CookCalendar() {
  const [value, setValue] = useState<Date | [Date, Date]>(new Date());
  const [recipes, setRecipes] = useState<StoredRecipe[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<StoredRecipe | null>(null);
  const { user, logout } = useAuth();
  const userName = useMemo(
    () => user?.name ?? localStorage.getItem("currentUserName") ?? TEXT.nav.myPage,
    [user?.name]
  );
  const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;

  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);

  useEffect(() => {
    const fetchRecipes = async () => {
      if (!userId) return;
      try {
        const data = await apiFetch<{ recipes?: StoredRecipe[] }>(
          `/get_selected_recipes?user_id=${encodeURIComponent(userId)}`
        );
        setRecipes(data.recipes ?? []);
      } catch (error) {
        console.error("Selected recipes fetch failed:", error);
      }
    };

    fetchRecipes();
  }, [userId]);

  const selectedDate = Array.isArray(value) ? value[0] : value;
  const formattedDate = selectedDate.toLocaleDateString("sv-SE");
  const recipesForDay = recipes.filter((item) => item.selected_date?.startsWith(formattedDate));

  return (
    <>
      <VideoBackgroundLayout contentClassName="text-[#6B2E00]" showVideo={false}>
        <header className="relative bg-transparent text-center pt-4 pb-2 sticky top-0 z-50">
          <h1 className="text-xl font-extrabold">CookUS</h1>
          <nav className="mt-2 flex justify-center gap-6 text-sm font-medium">
            <Link to="/" className="hover:text-[#8B4000]">
              {TEXT.nav.fridge}
            </Link>
            <span>|</span>
            <Link to="/calendar" className="font-bold text-[#8B4000]">
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

        <main className="flex-1 px-6 py-8 overflow-y-auto">
          <section className="mb-6 grid grid-cols-1 gap-3 text-sm text-white">
            <div className="rounded-3xl bg-[#F2994A]/80 px-4 py-3 shadow">
              <div className="flex items-center gap-3">
                <FaCalendarDay className="h-7 w-7 drop-shadow" />
                <div>
                  <p className="text-xs tracking-wide uppercase opacity-80">선택한 날짜</p>
                  <p className="text-lg font-semibold">{formattedDate}</p>
                </div>
              </div>
            </div>
            <div className="rounded-3xl bg-[#6B2E00]/70 px-4 py-3 shadow">
              <div className="flex items-center gap-3">
                <FaUtensils className="h-7 w-7 drop-shadow" />
                <div>
                  <p className="text-xs tracking-wide uppercase opacity-80">등록된 레시피</p>
                  <p className="text-lg font-semibold">{recipesForDay.length}개</p>
                </div>
              </div>
            </div>
          </section>

          <h2 className="text-2xl font-bold mb-4 text-[#6B2E00]">{TEXT.title}</h2>
          <div className="relative rounded-3xl border border-[#E2B857]/60 bg-white/85 shadow-xl overflow-hidden">
            <Calendar
              onChange={setValue}
              value={value}
              locale="ko-KR"
              className="w-full text-center"
              tileClassName={({ date }) => {
                const today = new Date();
                const formatted = date.toISOString().split("T")[0];
                const selectedFormatted = selectedDate.toISOString().split("T")[0];

                let classes = "py-2 rounded-xl transition-all duration-200 ";
                if (date.getDay() === 0) classes += "text-red-500 ";
                if (date.getDay() === 6) classes += "text-blue-500 ";
                if (formatted === today.toISOString().split("T")[0]) {
                  classes += "border-2 border-[#F2994A] font-bold text-[#6B2E00] ";
                }
                if (formatted === selectedFormatted) {
                  classes += "bg-[#F7D98A] text-[#6B2E00] font-extrabold shadow-sm ";
                }
                classes += "hover:bg-[#F7D98A]/60 hover:shadow cursor-pointer";
                return classes;
              }}
            />
          </div>

          <div className="w-full mt-8 space-y-4">
            {recipesForDay.length > 0 ? (
              recipesForDay.map((recipe, index) => (
                <div
                  key={`${recipe.recipe_nm_ko ?? "recipe"}-${index}`}
                  className="rounded-3xl bg-white/90 p-4 shadow-md border border-[#E2B857]/40 backdrop-blur"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-[#6B2E00]">
                      {recipe.recipe_nm_ko ?? TEXT.modal.defaultName}
                    </h3>
                    <div className="flex items-center gap-2 text-xs font-semibold text-[#6B2E00]/80">
                      <span className="rounded-full bg-[#F7D98A]/80 px-3 py-1">
                        {TEXT.level}: {recipe.level_nm ?? TEXT.modal.noInfo}
                      </span>
                      <span className="rounded-full bg-[#F7D98A]/50 px-3 py-1">
                        {TEXT.cookingTime}: {recipe.cooking_time ?? TEXT.modal.noInfo}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedRecipe(recipe)}
                    className="mt-3 w-full rounded-xl bg-[#F2994A] py-2 text-sm font-semibold text-white shadow hover:bg-[#f08a29]"
                  >
                    {TEXT.detailButton}
                  </button>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center rounded-3xl bg-white/70 border border-dashed border-[#E2B857]/60 py-8 text-[#6B2E00]/70">
                <FaUtensils className="h-10 w-10 mb-3 opacity-60" />
                <p className="text-sm font-medium">{TEXT.noRecipes}</p>
              </div>
            )}
          </div>
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

      {selectedRecipe && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center z-50">
          <div className="bg-[#FFF6E0] w-[360px] max-h-[500px] overflow-y-auto rounded-2xl shadow-xl p-5 relative">
            <button
              type="button"
              onClick={() => setSelectedRecipe(null)}
              className="absolute top-3 right-4 text-lg text-[#6B2E00]"
            >
              &times;
            </button>
            <h2 className="text-center font-extrabold text-[#6B2E00] text-lg mb-3">
              {selectedRecipe.recipe_nm_ko ?? TEXT.modal.defaultName}
            </h2>
            <p className="text-sm text-[#6B2E00]/80 mb-1">
              <b>{TEXT.level}:</b> {selectedRecipe.level_nm ?? TEXT.modal.noInfo}
            </p>
            <p className="text-sm text-[#6B2E00]/80 mb-1">
              <b>{TEXT.cookingTime}:</b> {selectedRecipe.cooking_time ?? TEXT.modal.noInfo}
            </p>
            <p className="text-sm text-[#6B2E00]/80 whitespace-pre-line">
              <b>{TEXT.modal.steps}</b>{" "}
              {selectedRecipe.step_text
                ?.replace(/\r\n/g, "\n")
                .replace(/\\n/g, "\n")
                .trim() || TEXT.modal.noInfo}
            </p>
            <div className="flex justify-center mt-4">
              <button
                type="button"
                onClick={() => setSelectedRecipe(null)}
                className="bg-[#F2994A] hover:bg-[#f08a29] text-white px-4 py-2 rounded-lg shadow"
              >
                {TEXT.modal.close}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
