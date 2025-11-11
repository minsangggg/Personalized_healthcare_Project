// src/components/AppFrame.tsx
import { Link, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

type Props = { title: string; children?: ReactNode };

export default function AppFrame({ title, children }: Props) {
  const loc = useLocation();
  const is = (p: string) => loc.pathname.startsWith(p);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* 헤더 */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "rgba(255,255,255,0.9)",
          backdropFilter: "blur(6px)",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <div
          style={{
            maxWidth: 480,
            margin: "0 auto",
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
          }}
        >
          <strong>{title}</strong>
          <span style={{ fontSize: 12, color: "#059669" }}>beta</span>
        </div>
      </header>

      {/* 본문 */}
      <main
        style={{
          flex: 1,
          maxWidth: 480,
          margin: "0 auto",
          width: "100%",
          padding: "12px 16px 72px", // 하단 탭 공간
          minHeight: 0,
        }}
      >
        {children ?? null}
      </main>

      {/* 하단 탭바 */}
      <nav
        style={{
          position: "sticky",
          bottom: 0,
          background: "rgba(255,255,255,0.95)",
          backdropFilter: "blur(6px)",
          borderTop: "1px solid #e5e7eb",
          paddingBottom: "env(safe-area-inset-bottom)",
        }}
      >
        <div
          style={{
            maxWidth: 480,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            height: 56,
          }}
        >
          <Tab to="/dashboard" active={is("/dashboard")}>대시보드</Tab>
          <Tab to="/pantry" active={is("/pantry")}>냉장고</Tab>
          <Tab to="/calendar" active={is("/calendar")}>캘린더</Tab>
          <Tab to="/mypage" active={is("/mypage")}>마이</Tab>
        </div>
      </nav>
    </div>
  );
}

function Tab({
  to,
  active,
  children,
}: {
  to: string;
  active?: boolean;
  children: ReactNode;
}) {
  return (
    <Link
      to={to}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12,
        fontWeight: active ? 700 : 500,
        color: active ? "#065f46" : "#6b7280",
        background: active ? "#ecfdf5" : "transparent",
        borderRadius: 9999,
        margin: 8,
      }}
    >
      <span>{children}</span>
    </Link>
  );
}
