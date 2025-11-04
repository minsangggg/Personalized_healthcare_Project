import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
} from "react";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";

import { useAuth } from "./AuthContext";
import SplashScreen from "./SplashScreen";
import { apiFetch } from "../api/client";

type IngredientItem = {
  name: string;
  amount: string;
};

type RecommendationItem = {
  recipe_id: string | number;
  recipe_nm_ko?: string;
  level_nm?: string;
  cooking_time?: string;
  step_text?: string;
  selected?: boolean;
};

const UserCircleIcon = FaUserCircle as ComponentType<{ className?: string }>;

export default function MainPage() {
  const [ingredients, setIngredients] = useState<IngredientItem[]>([]);
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [recommended, setRecommended] = useState<RecommendationItem[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<RecommendationItem | null>(null);
  const [showFridge, setShowFridge] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showRecommendModal, setShowRecommendModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const [userName, setUserName] = useState<string | null>(null);

  const { user, logout } = useAuth();
  const userId = useMemo(() => user?.id ?? localStorage.getItem("currentUser"), [user?.id]);

  useEffect(() => {
    const skipSplash = sessionStorage.getItem("skipSplash");
    if (skipSplash === "true") {
      setShowSplash(false);
      sessionStorage.removeItem("skipSplash");
    } else {
      const timer = setTimeout(() => setShowSplash(false), 2000);
      return () => clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    if (!userId) {
      setIngredients([]);
      setUserName(null);
      return;
    }

    const storageKey = `ingredients_${userId}`;
    const stored = JSON.parse(localStorage.getItem(storageKey) || "[]");
    setIngredients(stored);

    apiFetch<{ name?: string }>(`/get_user_name/${userId}`)
      .then((data) => {
        if (data.name) {
          setUserName(data.name);
          localStorage.setItem("currentUserName", data.name);
        }
      })
      .catch(() => {
        const cached = localStorage.getItem("currentUserName");
        if (cached) setUserName(cached);
      });
  }, [userId]);

  const persistIngredients = (items: IngredientItem[]) => {
    const key = userId ? `ingredients_${userId}` : "ingredients";
    localStorage.setItem(key, JSON.stringify(items));
    setIngredients(items);
  };

  const fetchIngredientSuggestions = useCallback(
    async (keyword: string) => {
      const params = new URLSearchParams();
      const trimmed = keyword.trim();
      if (trimmed) {
        params.set("keyword", trimmed);
      }
      params.set("limit", "15");
      const queryString = params.toString();
      const endpoint = queryString ? `/search_ingredient?${queryString}` : "/search_ingredient";

      try {
        const data = await apiFetch<{ results?: string[] }>(endpoint);
        setSearchResults(data.results ?? []);
      } catch (error) {
        console.error("Ingredient search failed:", error);
        setSearchResults([]);
      }
    },
    []
  );

  const handleSearch = (value: string) => {
    setSearch(value);
    void fetchIngredientSuggestions(value);
  };

  const addIngredient = (name: string) => {
    if (ingredients.some((item) => item.name === name)) return;
    const updated = [...ingredients, { name, amount: "1" }];
    persistIngredients(updated);
    setSearch("");
    void fetchIngredientSuggestions("");
  };

  useEffect(() => {
    if (showModal) {
      setSearch("");
      void fetchIngredientSuggestions("");
    } else {
      setSearchResults([]);
    }
  }, [showModal, fetchIngredientSuggestions]);

  const changeAmount = (name: string, delta: number) => {
    const updated = ingredients.map((item) =>
      item.name === name
        ? { ...item, amount: Math.max(1, Number(item.amount) + delta).toString() }
        : item
    );
    persistIngredients(updated);
  };

  const removeIngredient = (name: string) => {
    persistIngredients(ingredients.filter((item) => item.name !== name));
  };

  const saveFridgeToServer = async () => {
    if (!userId) {
      alert("濡쒓렇???꾩뿉 ?됱옣怨좊? ??ν븷 ???덉뒿?덈떎.");
      return;
    }
    try {
      await Promise.all(
        ingredients.map((item) =>
          apiFetch("/add_ingredient", {
            method: "POST",
            body: JSON.stringify({
              user_id: userId,
              name: item.name,
              amount: item.amount,
            }),
          })
        )
      );
      alert("?됱옣怨좉? ??λ릺?덉뒿?덈떎.");
    } catch (error) {
      console.error("Failed to save fridge:", error);
      alert("?됱옣怨???μ뿉 ?ㅽ뙣?덉뒿?덈떎.");
    }
  };

  const handleRecommend = async () => {
    if (!userId) {
      alert("濡쒓렇???꾩뿉 異붿쿇??諛쏆쓣 ???덉뒿?덈떎.");
      return;
    }
    setLoading(true);
    try {
      const data = await apiFetch<{ recommendations?: RecommendationItem[]; user_level?: string }>(
        "/recommend",
        {
          method: "POST",
          body: JSON.stringify({
            user_id: userId,
            ingredients: ingredients.map((item) => ({
              name: item.name,
              amount: item.amount,
            })),
          }),
        }
      );
      const list = (data.recommendations ?? []).map((item) => ({ ...item, selected: false }));
      setRecommended(list);
      setShowRecommendModal(true);
      if (data.user_level) {
        alert(`?꾩옱 ?붾━ ?덈꺼 ${data.user_level}??留욌뒗 ?덉떆?쇱엯?덈떎.`);
      }
    } catch (error) {
      console.error("異붿쿇 遺덈윭?ㅺ린 ?ㅽ뙣:", error);
      alert("異붿쿇??遺덈윭?ㅼ? 紐삵뻽?듬땲??");
    } finally {
      setLoading(false);
    }
  };

  const registerSelectedRecipes = async () => {
    if (!userId) {
      alert("癒쇱? 濡쒓렇?명빐 二쇱꽭??");
      return;
    }
    const selected = recommended.filter((recipe) => recipe.selected);
    if (selected.length === 0) {
      alert("理쒖냼 ??媛??댁긽???덉떆?쇰? ?좏깮??二쇱꽭??");
      return;
    }
    try {
      await apiFetch("/register_selected", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          recipes: selected.map((recipe) => recipe.recipe_id),
        }),
      });
      alert("?좏깮???덉떆?쇨? ??λ릺?덉뒿?덈떎.");
      setShowRecommendModal(false);
    } catch (error) {
      console.error("?덉떆??????ㅽ뙣:", error);
      alert("?덉떆?쇰? ??ν븯吏 紐삵뻽?듬땲??");
    }
  };

  if (showSplash) {
    return <SplashScreen onFinish={() => setShowSplash(false)} />;
  }

  return (
    <div className="min-h-screen flex justify-center bg-[#FFFDF6] py-6 overflow-y-auto">
      <div className="w-[430px] min-h-[95vh] bg-[#F7D98A] rounded-2xl shadow-lg flex flex-col overflow-hidden">
        <header className="bg-[#F7D98A] border-b border-[#D7B78A] text-center pt-4 pb-2 relative">
          <h1 className="text-[#6B2E00] text-xl font-extrabold">CookUS</h1>
          <nav className="flex justify-center gap-6 text-[#6B2E00] font-medium text-[15px] mt-2">
            <Link to="/" className="hover:text-[#8B4000]">
              硫붿씤
            </Link>
            <span>|</span>
            <Link to="/calendar" className="hover:text-[#8B4000]">
              罹섎┛??            </Link>
            <span>|</span>
            <Link to="/dashboard" className="hover:text-[#8B4000]">
              ??쒕낫??            </Link>
            <span>|</span>
            {user ? (
              <button onClick={logout} className="text-[#6B2E00] hover:text-[#8B4000]">
                濡쒓렇?꾩썐
              </button>
            ) : (
              <Link to="/login" className="hover:text-[#8B4000]">
                濡쒓렇??              </Link>
            )}
          </nav>
          <Link
            to="/mypage"
            className="absolute right-4 top-4 flex flex-col items-center text-xs font-semibold text-[#6B2E00] hover:text-[#8B4000] transition"
          >
            <UserCircleIcon className={`w-7 h-7 ${user ? "text-[#6B2E00]" : "text-gray-400"}`} />
            <span>{userName ?? "留덉씠?섏씠吏"}</span>
          </Link>
        </header>

        <main className="flex-1 flex flex-col gap-6 p-6 overflow-y-auto">
          <section className="bg-white/70 rounded-xl shadow-inner p-4">
            <button
              type="button"
              onClick={() => setShowFridge((prev) => !prev)}
              className="w-full text-left font-semibold text-[#6B2E00]"
            >
              ???됱옣怨??щ즺 蹂닿린 ({ingredients.length}媛?
            </button>
            {showFridge && (
              <ul className="mt-3 space-y-1 text-sm text-[#6B2E00]">
                {ingredients.length === 0 ? (
                  <li>??λ맂 ?щ즺媛 ?놁뒿?덈떎.</li>
                ) : (
                  ingredients.map((item) => (
                    <li key={item.name}>
                      {item.name} : {item.amount}
                    </li>
                  ))
                )}
              </ul>
            )}
          </section>

          <section className="flex gap-3 flex-wrap justify-center">
            <button
              type="button"
              onClick={() => setShowModal(true)}
              className="px-4 py-2 rounded-lg bg-[#FFF6E0] text-[#6B2E00] shadow hover:bg-[#ffedc4]"
            >
              ?щ즺 異붽?
            </button>
            <button
              type="button"
              onClick={handleRecommend}
              className="px-4 py-2 rounded-lg bg-[#F2994A] text-white shadow hover:bg-[#f08a29]"
            >
              ?덉떆??異붿쿇諛쏄린
            </button>
            <button
              type="button"
              onClick={() => {
                if (window.confirm("?됱옣怨??щ즺瑜?紐⑤몢 ??젣?좉퉴??")) {
                  persistIngredients([]);
                }
              }}
              className="px-4 py-2 rounded-lg bg-[#ffe4cc] text-[#6B2E00] shadow hover:bg-[#ffd3ac]"
            >
              珥덇린??            </button>
            <button
              type="button"
              onClick={saveFridgeToServer}
              className="px-4 py-2 rounded-lg bg-[#6B2E00] text-white shadow hover:bg-[#4c2100]"
            >
              ?됱옣怨????            </button>
          </section>

          {loading && (
            <div className="text-center text-[#6B2E00] font-semibold">異붿쿇??以鍮꾪븯怨??덉뒿?덈떎??/div>
          )}
        </main>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex justify-center items-center z-50">
          <div className="bg-[#FFF2D9] w-[360px] rounded-2xl shadow-lg p-5 relative">
            <button
              type="button"
              onClick={() => setShowModal(false)}
              className="absolute top-3 right-4 text-lg text-[#6B2E00]"
            >
              횞
            </button>
            <h2 className="text-center text-[#6B2E00] font-bold text-lg mb-3">?щ즺 愿由?/h2>
            <input
              type="text"
              value={search}
              onChange={(event) => handleSearch(event.target.value)}
              placeholder="?щ즺紐낆쓣 ?낅젰?섏꽭??
              className="w-full p-2 border border-[#D7B78A] rounded-lg text-center mb-2"
            />
            {searchResults.length > 0 ? (
              <ul className="bg-white rounded-lg border border-[#D7B78A] p-2 max-h-32 overflow-y-auto mb-3 text-left">
                {searchResults.map((item) => (
                  <li
                    key={item}
                    onClick={() => addIngredient(item)}
                    className="cursor-pointer hover:bg-[#F7D98A] px-2 py-1 rounded"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-center text-[#6B2E00] text-sm mb-3">寃??寃곌낵媛 ?놁뒿?덈떎.</p>
            )}

            <div className="space-y-2">
              {ingredients.map((item) => (
                <div key={item.name} className="flex justify-between items-center bg-[#FFEFC3] rounded-lg p-2">
                  <span className="font-medium">{item.name}</span>
                  <div className="flex items-center gap-1">
                    <button onClick={() => changeAmount(item.name, -1)} className="px-2">
                      -
                    </button>
                    <span>{item.amount}</span>
                    <button onClick={() => changeAmount(item.name, 1)} className="px-2">
                      +
                    </button>
                    <button onClick={() => removeIngredient(item.name)} className="text-sm text-red-500 ml-2">
                      ??젣
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-center gap-4 mt-4">
              <button
                type="button"
                onClick={() => {
                  setShowModal(false);
                  saveFridgeToServer();
                }}
                className="bg-[#6B2E00] text-white px-4 py-2 rounded-xl"
              >
                ???              </button>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="bg-[#FFFDF6] text-[#6B2E00] px-4 py-2 rounded-xl"
              >
                痍⑥냼
              </button>
            </div>
          </div>
        </div>
      )}

      {showRecommendModal && (
        <div className="fixed inset-0 bg-black/40 flex justify-center items-center z-50">
          <div className="bg-[#FFF2D9] w-[400px] rounded-2xl shadow-xl p-5 relative max-h-[90vh] overflow-y-auto">
            <button
              type="button"
              onClick={() => setShowRecommendModal(false)}
              className="absolute top-3 right-4 text-lg text-[#6B2E00]"
            >
              횞
            </button>
            <h2 className="text-center text-[#6B2E00] font-extrabold text-xl mb-5">異붿쿇 ?덉떆??/h2>
            <div className="grid grid-cols-1 gap-4">
              {recommended.length === 0 && (
                <p className="text-sm text-center text-[#6B2E00]">異붿쿇 寃곌낵媛 ?놁뒿?덈떎.</p>
              )}
              {recommended.map((recipe, index) => (
                <div
                  key={recipe.recipe_id ?? index}
                  className={`bg-[#FFF8E1] p-3 rounded-xl shadow-md border ${
                    recipe.selected ? "border-[#F2994A]" : "border-transparent"
                  } cursor-pointer`}
                  onClick={() =>
                    setRecommended((prev) =>
                      prev.map((item, idx) =>
                        idx === index ? { ...item, selected: !item.selected } : item
                      )
                    )
                  }
                >
                  <h3 className="font-bold text-[#6B2E00] text-md mb-2">
                    {recipe.recipe_nm_ko ?? "?덉떆??}
                  </h3>
                  <p className="text-xs text-[#6B2E00]/80">
                    ?쒖씠?? {recipe.level_nm ?? "?뺣낫 ?놁쓬"} / 議곕━?쒓컙: {recipe.cooking_time ?? "?뺣낫 ?놁쓬"}
                  </p>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      setSelectedRecipe(recipe);
                    }}
                    className="mt-3 bg-[#F2994A] hover:bg-[#f08a29] text-white text-sm font-semibold py-1.5 rounded-lg shadow w-full"
                  >
                    ?곸꽭 蹂닿린
                  </button>
                </div>
              ))}
            </div>

            {recommended.length > 0 && (
              <div className="flex justify-center gap-4 mt-6">
                <button
                  type="button"
                  onClick={registerSelectedRecipes}
                  className="bg-[#F2994A] hover:bg-[#f08a29] text-white px-5 py-2 rounded-xl"
                >
                  ???                </button>
                <button
                  type="button"
                  onClick={() => setShowRecommendModal(false)}
                  className="bg-[#FFFDF6] text-[#6B2E00] px-5 py-2 rounded-xl shadow"
                >
                  ?リ린
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedRecipe && (
        <div className="fixed inset-0 bg-black/40 flex justify-center items-center z-50">
          <div className="bg-[#FFF6E0] w-[360px] max-h-[500px] overflow-y-auto rounded-2xl shadow-xl p-5 relative">
            <button
              type="button"
              onClick={() => setSelectedRecipe(null)}
              className="absolute top-3 right-4 text-lg text-[#6B2E00]"
            >
              횞
            </button>
            <h2 className="text-center font-extrabold text-[#6B2E00] text-lg mb-3">
              {selectedRecipe.recipe_nm_ko ?? "?덉떆??}
            </h2>
            <p className="text-sm text-[#6B2E00]/80 mb-1">
              <b>?쒖씠??</b> {selectedRecipe.level_nm ?? "?뺣낫 ?놁쓬"}
            </p>
            <p className="text-sm text-[#6B2E00]/80 mb-1">
              <b>議곕━?쒓컙:</b> {selectedRecipe.cooking_time ?? "?뺣낫 ?놁쓬"}
            </p>
            <p className="text-sm text-[#6B2E00]/80 whitespace-pre-line">
              <b>議곕━ 諛⑸쾿:</b>{" "}
              {selectedRecipe.step_text
                ?.replace(/\r\n/g, "\n")
                .replace(/\\n/g, "\n")
                .trim() || "議곕━ 諛⑸쾿 ?뺣낫媛 ?놁뒿?덈떎."}
            </p>
            <div className="flex justify-center mt-4">
              <button
                type="button"
                onClick={() => setSelectedRecipe(null)}
                className="bg-[#F2994A] hover:bg-[#f08a29] text-white px-4 py-2 rounded-lg shadow"
              >
                ?リ린
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

