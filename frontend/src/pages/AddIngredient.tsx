import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function AddIngredient() {
  const [ingredient, setIngredient] = useState("");
  const [sauce, setSauce] = useState("");
  const navigate = useNavigate();

  const handleSave = () => {
    const savedIngredients: string[] = JSON.parse(localStorage.getItem("ingredients") || "[]");
    const savedSauces: string[] = JSON.parse(localStorage.getItem("sauces") || "[]");

    if (ingredient.trim()) savedIngredients.push(ingredient.trim());
    if (sauce.trim()) savedSauces.push(sauce.trim());

    localStorage.setItem("ingredients", JSON.stringify(savedIngredients));
    localStorage.setItem("sauces", JSON.stringify(savedSauces));

    alert("재료가 저장되었습니다!");
    navigate("/");
  };

  return (
    <div className="min-h-screen flex justify-center items-center bg-[#FFFDF6]">
      <div className="w-[400px] bg-[#F7D98A] rounded-2xl shadow-xl p-6 text-center">
        <h2 className="text-[#6B2E00] font-extrabold text-xl mb-6">재료 추가</h2>

        <div className="flex flex-col gap-4 mb-6">
          <input
            type="text"
            placeholder="재료를 입력하세요"
            value={ingredient}
            onChange={(event) => setIngredient(event.target.value)}
            className="w-full p-3 rounded-md border border-[#D7B78A] focus:outline-none"
          />
          <input
            type="text"
            placeholder="소스를 입력하세요"
            value={sauce}
            onChange={(event) => setSauce(event.target.value)}
            className="w-full p-3 rounded-md border border-[#D7B78A] focus:outline-none"
          />
        </div>

        <div className="flex justify-center gap-4">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="bg-[#FFF6E0] text-[#6B2E00] font-semibold px-5 py-2 rounded-lg hover:bg-[#fff2cc]"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="bg-[#F2994A] text-white font-semibold px-5 py-2 rounded-lg hover:bg-[#f08a29]"
          >
            저장
          </button>
        </div>
      </div>
    </div>
  );
}
