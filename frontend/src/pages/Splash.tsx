import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function Splash() {
  const nav = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => nav("/login", { replace: true }), 2000);
    return () => clearTimeout(timer);
  }, [nav]);

  return (
    <div style={container}>
      <div style={card}>
        <h1 style={{ margin: 0, fontSize: 28, color: "#111827" }}>🍳 오늘부터, 나만의 레시피</h1>
        <p style={{ color: "#6b7280", marginTop: 12 }}>냉장고 속 재료로 간편하고 건강하게 요리해보세요!</p>
      </div>
    </div>
  );
}

const container: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  height: "100vh",
  background: "#f3f4f6",
};

const card: React.CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  padding: 32,
  boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
  textAlign: "center",
};
