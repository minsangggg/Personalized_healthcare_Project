import React from "react";

export default function Recipes() {
  return (
    <div style={pageStyle}>
      <h2>레시피 추천</h2>
      <p>AI가 회원님의 취향과 재료에 맞는 레시피를 추천해드립니다.</p>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  padding: 32,
  textAlign: "center",
};
