import React, { useEffect } from "react";

export default function SplashScreen({ onFinish }: { onFinish: () => void }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onFinish();
    }, 6000); // 🎥 영상 길이(메인으로 전환)
    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <div
      className="w-full h-screen flex justify-center items-center bg-black relative overflow-hidden transition-opacity duration-1000"
      style={{ opacity: 1 }}
    >
      <video
        autoPlay
        muted
        playsInline
        onEnded={onFinish} // 영상이 끝나면 즉시 넘어감
        className="absolute top-0 left-0 w-full h-full object-contain"
      >
        <source src="/video/intro.mp4" type="video/mp4" />
      </video>

      {/* 로고나 텍스트 겹쳐서 보여주기 */}
      <h1 className="relative z-10 text-white text-3xl font-extrabold tracking-wider drop-shadow-lg">
        CookUS
      </h1>
    </div>
  );
}
