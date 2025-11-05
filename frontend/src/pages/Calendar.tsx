import React, { useEffect, useMemo, useState, type ComponentType } from "react";
import Calendar from "react-calendar";
import "react-calendar/dist/Calendar.css";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";
import { FiPlus, FiTrash2 } from "react-icons/fi";

import { useAuth } from "./AuthContext";
import { apiFetch } from "../api/client";
import VideoBackgroundLayout from "../components/VideoBackgroundLayout";

type StoredRecipe = {
  recipe_id?: string | number;
  recommend_id?: number;
  recipe_nm_ko?: string;
  selected_date?: string;
  level_nm?: string;
  cooking_time?: string;
  step_text?: string;
  action?: number;
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
  title: "요리 캘린더",
  selectedDatePrefix: "선택한 날짜:",
  noRecipes: "해당 날짜에 저장된 레시피가 없습니다.",
  level: "난이도",
  cookingTime: "조리시간",
  detailButton: "상세 보기",
  footer: {
    title: "2025 Recipe Market",
    about: "소개",
    notice: "공지사항",
    faq: "FAQ",
    contact: "Recipe Market | 123-45-6789 | +82-1234-4567",
    email: "hello@recipemarket.com",
    policy: "이용약관 | 개인정보처리방침",
  },
  modal: {
    defaultName: "레시피",
    steps: "조리 순서:",
    close: "닫기",
    noInfo: "조리 순서 정보가 없습니다.",
  },
};

export default function CookCalendar() {
  const [value, setValue] = useState<Date | [Date, Date]>(new Date());
  const [recipes, setRecipes] = useState<StoredRecipe[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<StoredRecipe | null>(null);
  const { user, logout } = useAuth();
  const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;
  const PlusIcon = FiPlus as ComponentType<{ className?: string }>;
  const TrashIcon = FiTrash2 as ComponentType<{ className?: string }>;

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

  const handleActionUpdate = async (recipe: StoredRecipe, nextAction: number) => {
    if (!userId) {
      alert("로그인 후 이용해 주세요.");
      return;
    }
    if (recipe.recommend_id == null || recipe.recipe_id == null) {
      alert("레시피 정보를 다시 불러와 주세요.");
      return;
    }

    try {
      await apiFetch("/selected_recipe/action", {
        method: "PATCH",
        body: JSON.stringify({
          user_id: userId,
          recommend_id: recipe.recommend_id,
          recipe_id: recipe.recipe_id,
          action: nextAction,
        }),
      });
      setRecipes((prev) =>
        prev.map((item) =>
          item.recipe_id === recipe.recipe_id && item.recommend_id === recipe.recommend_id
            ? { ...item, action: nextAction }
            : item
        )
      );
    } catch (error) {
      console.error("Failed to update recipe action:", error);
      alert("상태를 변경하지 못했습니다.");
    }
  };

const handleDeleteRecipe = async (recipe: StoredRecipe) => {
  if (!userId) {
    alert("�α��� �� �̿��� �ּ���.");
    return;
  }
  if (recipe.recommend_id == null || recipe.recipe_id == null) {
    alert("������ ������ �ٽ� �ҷ��� �ּ���.");
    return;
  }

  try {
    await apiFetch("/selected_recipe", {
      method: "DELETE",
      body: JSON.stringify({
        user_id: userId,
        recommend_id: recipe.recommend_id,
        recipe_id: recipe.recipe_id,
      }),
    });
    setRecipes((prev) =>
      prev.filter(
        (item) =>
          !(
            String(item.recipe_id) === String(recipe.recipe_id) &&
            String(item.recommend_id) === String(recipe.recommend_id)
          )
      )
    );
    setSelectedRecipe((current) => {
      if (
        current &&
        String(current.recipe_id) === String(recipe.recipe_id) &&
        String(current.recommend_id) === String(recipe.recommend_id)
      ) {
        return null;
      }
      return current;
    });
  } catch (error) {
    console.error("Failed to delete selected recipe:", error);
    alert("������ �������� ���߽��ϴ�.");
  }
};

  return (
    <>
      <style>
        {`
          .cook-calendar.react-calendar {
            background: transparent !important;
            border: none !important;
            color: #ffffff;
          }
          .cook-calendar .react-calendar__navigation {
            background: transparent;
            border-bottom: none;
          }
          .cook-calendar .react-calendar__navigation button {
            color: #ffffff;
            background: transparent !important;
          }
          .cook-calendar .react-calendar__month-view__weekdays {
            color: rgba(255, 255, 255, 0.8);
          }
          .cook-calendar
            .react-calendar__month-view__days__day--weekend {
            color: #ffffff !important;
          }
          .cook-calendar .react-calendar__tile {
            background: transparent !important;
            color: #ffffff;
          }
          .cook-calendar .react-calendar__tile--active,
          .cook-calendar .react-calendar__tile--now {
            background: transparent !important;
            color: inherit !important;
          }
          .cook-calendar .react-calendar__tile:enabled:hover,
          .cook-calendar .react-calendar__tile:enabled:focus {
            background: rgba(255, 255, 255, 0.2) !important;
          }
        `}
      </style>
      <VideoBackgroundLayout contentClassName="text-[#6B2E00]">
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

        <main className="flex-1 px-6 pb-8 flex flex-col">
          <div className="mt-3 text-center text-white drop-shadow-[0_4px_8px_rgba(0,0,0,0.35)]">
            <p className="text-2xl font-extrabold tracking-tight">{TEXT.title}</p>
            <p className="text-sm font-medium text-white/80 mt-1">
              {TEXT.selectedDatePrefix} {formattedDate}
            </p>
          </div>

          <div className="mt-6 flex justify-center">
            <div className="w-full max-w-[360px] rounded-[28px] px-4 py-5">
              <Calendar
                onChange={setValue}
                value={value}
                locale="ko-KR"
                className="cook-calendar w-full text-center rounded-2xl text-white"
                tileClassName={({ date }) => {
                  const today = new Date();
                  const todayFormatted = today.toISOString().split("T")[0];
                  const formatted = date.toISOString().split("T")[0];
                  const selectedFormatted = selectedDate.toISOString().split("T")[0];

                  const isToday = formatted === todayFormatted;
                  const isSelected = formatted === selectedFormatted;

                  const classes = [
                    "py-3",
                    "rounded-full",
                    "text-sm",
                    "font-semibold",
                    "transition",
                    "duration-200",
                    "text-white",
                    "bg-transparent",
                    "cursor-pointer",
                    "hover:bg-white/20",
                  ];

                  if (isSelected) {
                    classes.push(
                      "ring-2",
                      "ring-white",
                      "bg-white/10",
                      "text-white"
                    );
                  } else if (isToday) {
                    classes.push(
                      "bg-white",
                      "text-[#6B2E00]",
                      "shadow-lg"
                    );
                  }

                  return classes.join(" ");
                }}
              />
            </div>
          </div>

          <div className="mt-6 space-y-4 px-2">
            {recipesForDay.length > 0 ? (
              recipesForDay.map((recipe, index) => {
                const isActive = recipe.action === 1;
                return (
                  <div
                    key={`${recipe.recipe_nm_ko ?? "recipe"}-${index}`}
                    className={`text-[#6B2E00] bg-white/20 backdrop-blur-sm border border-white/10 rounded-2xl px-3 py-3 transition ${isActive ? "font-semibold" : ""}`}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-[#6B2E00]">
                        {recipe.recipe_nm_ko ?? TEXT.modal.defaultName}
                      </h3>
                      <span
                        className={`text-xs font-semibold px-3 py-1 rounded-full ${isActive ? "bg-[#F7D98A] text-[#6B2E00]" : "bg-[#EEE1C5] text-[#6B2E00]/70"}`}
                      >
                        {isActive ? "진행완료" : "진행 전"}
                      </span>
                    </div>
                    <p className="text-sm text-[#6B2E00]/70 mt-1">
                      {TEXT.level}: {recipe.level_nm ?? TEXT.modal.noInfo} / {TEXT.cookingTime}: {recipe.cooking_time ?? TEXT.modal.noInfo}
                    </p>
                    <div className="mt-3 flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleActionUpdate(recipe, isActive ? 0 : 1)}
                          className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition ${
                            isActive
                              ? "border-[#F7D98A] bg-[#F7D98A]/80 text-[#6B2E00] shadow-md"
                              : "border-white/50 bg-white/20 text-white hover:bg-white/30"
                          }`}
                          aria-label={isActive ? "숨기기" : "표시하기"}
                        >
                          <PlusIcon className={`h-3.5 w-3.5 ${isActive ? "rotate-45" : ""}`} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteRecipe(recipe)}
                          className="flex h-8 w-8 items-center justify-center rounded-full border border-white/50 bg-white/10 text-white transition hover:bg-white/20 hover:text-[#B84000]"
                          aria-label="삭제"
                        >
                          <TrashIcon className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedRecipe(recipe)}
                        className="ml-auto rounded-xl bg-[#F2994A] px-4 py-2 text-sm font-semibold text-[#6B2E00] shadow hover:bg-[#f08a29]"
                      >
                        {TEXT.detailButton}
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-center text-sm text-[#6B2E00]/60">{TEXT.noRecipes}</p>
            )}
          </div>
        </main>
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








