import React, { useState } from "react";

import { apiFetch } from "../api/client";

type Recommendation = {
  recipe_id?: string | number;
  recipe_name?: string;
  match_count?: number;
  match_ratio?: number;
  level?: string;
};

export default function Recommend() {
  const [recipes, setRecipes] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const userId = localStorage.getItem("currentUser");

  const requestRecommendations = async () => {
    if (!userId) {
      alert("로그인 후 추천 기능을 이용할 수 있습니다.");
      return;
    }

    setLoading(true);
    try {
      const data = await apiFetch<{ user_level?: string; recommendations?: Recommendation[] }>("/recommend", {
        method: "POST",
        body: JSON.stringify({
          user_id: userId,
          ingredients: [],
        }),
      });

      setRecipes(data.recommendations ?? []);
      if (data.user_level) {
        alert(`현재 요리 레벨 ${data.user_level}에 맞는 추천입니다.`);
      }
    } catch (error) {
      console.error("추천 요청 실패:", error);
      const message = error instanceof Error ? error.message : "추천을 불러오지 못했습니다.";
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-xl p-6 text-center">
        <video
          className="w-full h-56 rounded-xl object-cover shadow-md"
          src="https://cdn.pixabay.com/video/2023/03/10/153094-808053935_tiny.mp4"
          autoPlay
          muted
          loop
        />

        <h1 className="mt-6 text-2xl font-bold text-gray-800">AI 레시피 추천</h1>
        <p className="text-gray-500 mt-2">
          버튼을 눌러 냉장고 재료와 요리 레벨에 맞는 레시피를 받아보세요.
        </p>

        <button
          type="button"
          onClick={requestRecommendations}
          disabled={loading}
          className="mt-5 px-6 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-full shadow hover:scale-105 transition-transform duration-200 disabled:opacity-50"
        >
          {loading ? "추천을 불러오는 중입니다…" : "추천 받기"}
        </button>
      </div>

      {recipes.length > 0 && (
        <div className="mt-8 space-y-4">
          {recipes.map((recipe, index) => (
            <div key={recipe.recipe_id ?? index} className="p-4 bg-white rounded-xl shadow-md hover:shadow-lg transition">
              <h3 className="text-lg font-semibold text-gray-800">{recipe.recipe_name ?? "레시피"}</h3>
              <p className="text-sm text-gray-500 mt-1">
                매칭된 재료 수: {recipe.match_count ?? 0}개 ({recipe.match_ratio ?? 0}%)
              </p>
              <p className="text-xs text-emerald-600 font-medium mt-2">난이도: {recipe.level ?? "정보 없음"}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
