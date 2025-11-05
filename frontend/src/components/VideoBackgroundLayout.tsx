import React from "react";

const VIDEO_SRC = "/video/kitchen.mp4";

type Props = {
  children: React.ReactNode;
  contentClassName?: string;
  showVideo?: boolean;
};

export default function VideoBackgroundLayout({
  children,
  contentClassName = "",
  showVideo = true,
}: Props) {
  return (
    <div className="min-h-screen bg-[#FCE7C8] py-8 flex justify-center px-4">
      <div className="relative w-full max-w-[430px] min-h-[95vh] rounded-[32px] shadow-[0_18px_45px_rgba(107,46,0,0.25)] overflow-hidden">
        {showVideo ? (
          <video
            className="absolute inset-0 h-full w-full object-cover"
            autoPlay
            loop
            muted
            playsInline
            src={VIDEO_SRC}
          />
        ) : (
          <div className="absolute inset-0 bg-[#F7D98A]" />
        )}
        <div className="absolute inset-0 bg-[#8C5C2D]/15" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#F7D98A]/40 via-[#F7D98A]/85 to-[#DFAD72]" />
        <div
          className={`relative z-10 flex h-full w-full flex-col overflow-hidden ${contentClassName}`.trim()}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
