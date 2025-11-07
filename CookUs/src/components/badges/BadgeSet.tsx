import React from 'react'

/*
  CookUS Badge Set (SVG + React)
  - viewBox: 0 0 64 64 (24~64px 권장)
  - CSS 변수: --badge-primary, --badge-accent, --badge-bg, --badge-stroke
  - 잠금 처리: earned=false일 때 grayscale + opacity 적용
*/

// Themeable colors
const stroke = 'var(--badge-stroke, #4B5563)'
const bg = 'var(--badge-bg, #FFF7DD)'
const p1 = 'var(--badge-primary, #FF8A00)'
const p2 = 'var(--badge-accent, #7C4DFF)'

const Grad = ({ id = 'g' }: { id?: string }) => (
  <defs>
    <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stopColor={p1} />
      <stop offset="100%" stopColor={p2} />
    </linearGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity=".25" />
    </filter>
  </defs>
)

// Bases
const Medal: React.FC<{ ring?: boolean; children: React.ReactNode }> = ({ ring = true, children }) => (
  <svg viewBox="0 0 64 64" style={{ display: 'block' }}>
    <Grad id="gm" />
    <circle cx="32" cy="32" r="26" fill={bg} stroke={stroke} strokeWidth={2} filter="url(#soft)" />
    <path d="M22 10 L32 18 L42 10 L42 6 L22 6 Z" fill="url(#gm)" stroke={stroke} strokeWidth={1.5} />
    <path d="M18 40 L26 38 L32 44 L38 38 L46 40 L40 54 L32 48 L24 54 Z" fill="url(#gm)" stroke={stroke} strokeWidth={1.5} />
    {ring && <circle cx="32" cy="32" r="23" fill="none" stroke="url(#gm)" strokeWidth={2} strokeDasharray="6 6" opacity={0.6} />}
    <g transform="translate(32 30)">{children}</g>
  </svg>
)

const Shield: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg viewBox="0 0 64 64" style={{ display: 'block' }}>
    <Grad id="gs" />
    <path d="M32 6 L50 12 V30 C50 41 42 51 32 56 C22 51 14 41 14 30 V12 Z" fill={bg} stroke={stroke} strokeWidth={2} filter="url(#soft)" />
    <path d="M32 8 L48 14 V30 C48 39 41 47 32 52 C23 47 16 39 16 30 V14 Z" fill="url(#gs)" opacity={0.15} />
    <g transform="translate(32 30)">{children}</g>
  </svg>
)

const Sticker: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg viewBox="0 0 64 64" style={{ display: 'block' }}>
    <Grad id="gt" />
    <rect x="8" y="10" width="48" height="44" rx="12" fill={bg} stroke={stroke} strokeWidth={2} filter="url(#soft)" />
    <circle cx="52" cy="14" r="6" fill="url(#gt)" stroke={stroke} strokeWidth={1.5} />
    <g transform="translate(32 32)">{children}</g>
  </svg>
)

// Glyphs
const Crown = () => (
  <g stroke={stroke} strokeWidth={1.6} fill="url(#gm)">
    <path d="M-12 6 H12 V10 H-12 Z" />
    <path d="M-12 6 L-6 -6 L0 4 L6 -6 L12 6 Z" />
  </g>
)

const Trophy = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <rect x="-8" y="-10" width="16" height="14" rx="2" />
    <path d="M-8 -8 H-14 C-14 -4 -10 -2 -8 -2 Z M8 -8 H14 C14 -4 10 -2 8 -2 Z" fill="url(#gm)" />
    <rect x="-6" y="4" width="12" height="3" />
    <rect x="-10" y="7" width="20" height="4" />
  </g>
)

const Star = () => (
  <g stroke={stroke} strokeWidth={1.6} fill="url(#gm)">
    <path d="M0 -12 L3 -4 L12 -4 L5 2 L8 10 L0 6 L-8 10 L-5 2 L-12 -4 L-3 -4 Z" />
  </g>
)

const Heart = () => (
  <g stroke={stroke} strokeWidth={1.6} fill="url(#gm)">
    <path d="M0 10 C-10 4 -12 -4 -6 -8 C-2 -10 2 -8 4 -6 C6 -8 10 -10 14 -6 C20 -2 10 6 0 10 Z" />
  </g>
)

const Chat = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <rect x="-12" y="-8" width="24" height="14" rx="3" />
    <path d="M-6 6 L-2 0 H6 L2 6 Z" />
  </g>
)

const Megaphone = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <path d="M-12 -4 L4 -8 L4 8 L-12 4 Z" />
    <rect x="4" y="-3" width="4" height="6" rx="1" fill="url(#gm)" />
  </g>
)

const Chef = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <circle cx="0" cy="-6" r="6" fill="url(#gm)" />
    <rect x="-8" y="-2" width="16" height="12" rx="3" />
  </g>
)

const CalendarIcon = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <rect x="-10" y="-8" width="20" height="16" rx="2" />
    <line x1="-10" y1="-3" x2="10" y2="-3" />
    <rect x="-7" y="0" width="4" height="4" rx="1" fill="url(#gm)" />
    <rect x="1" y="0" width="4" height="4" rx="1" fill="url(#gm)" />
  </g>
)

const Pan = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <circle cx="0" cy="2" r="8" />
    <rect x="6" y="-6" width="10" height="3" rx="1" />
  </g>
)

const KnifeFork = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <rect x="-8" y="-10" width="2" height="20" />
    <rect x="2" y="-10" width="2" height="20" />
  </g>
)

const Check = () => (
  <g stroke={stroke} strokeWidth={2} fill="none">
    <path d="M-8 0 L-2 6 L10 -6" />
  </g>
)

const Bolt = () => (
  <g stroke={stroke} strokeWidth={1.6} fill="url(#gm)">
    <path d="M-4 -14 L8 -2 H2 L6 10 L-6 -2 H0 Z" />
  </g>
)

const Fridge = () => (
  <g stroke={stroke} strokeWidth={1.6} fill={bg}>
    <rect x="-12" y="-14" width="24" height="28" rx="3" />
    <rect x="-12" y="-2" width="24" height="12" rx="2" fill="url(#gm)" opacity={0.2} />
    <line x1="-12" y1="-2" x2="12" y2="-2" />
    <rect x="8" y="-10" width="2.5" height="6" rx="1" fill={stroke} />
    <rect x="8" y="2" width="2.5" height="6" rx="1" fill={stroke} />
  </g>
)

const Flame = () => (
  <g stroke={stroke} strokeWidth={1.6} fill="url(#gm)">
    <path d="M0 -10 C4 -6 6 -2 6 2 C6 8 2 12 0 12 C-2 12 -6 8 -6 2 C-6 -2 -4 -6 0 -10 Z" />
    <circle cx="0" cy="3" r="4" fill={bg} opacity={0.4} />
  </g>
)

// Badge variants
export const B_FirstContest = () => (<Medal><Bolt/></Medal>)
export const B_TopChef = () => (<Medal><Crown/></Medal>)
export const B_Contest5 = () => (<Medal><Star/></Medal>)
export const B_Contest10 = () => (<Medal><Flame/></Medal>)
export const B_Contest20 = () => (<Medal><Trophy/></Medal>)
export const B_Top5Rank = () => (<Medal><Star/></Medal>)
export const B_Likes50 = () => (<Medal><Heart/></Medal>)
export const B_Posts10 = () => (<Medal><Chat/></Medal>)
export const B_Posts30 = () => (<Medal><Chat/></Medal>)
export const B_Posts50 = () => (<Medal><Chat/></Medal>)
export const B_Influencer = () => (<Medal><Megaphone/></Medal>)

export const B_RecFirst = () => (<Sticker><Chef/></Sticker>)
export const B_RecStreak5 = () => (<Sticker><CalendarIcon/></Sticker>)
export const B_Cooked1 = () => (<Sticker><Pan/></Sticker>)
export const B_Cooked10 = () => (<Sticker><KnifeFork/></Sticker>)
export const B_Cooked50 = () => (<Sticker><Trophy/></Sticker>)
export const B_Ingredient10 = () => (<Sticker><Fridge/></Sticker>)

export const B_Goal1 = () => (<Shield><Check/></Shield>)
export const B_Goal5 = () => (<Shield><Star/></Shield>)

// Map codes -> components
const MAP: Record<string, React.FC> = {
  first_contest: B_FirstContest,
  contest_rank_1: B_TopChef,
  contests_5: B_Contest5,
  contests_10: B_Contest10,
  contests_20: B_Contest20,
  contest_rank_top5: B_Top5Rank,
  likes_50_plus: B_Likes50,
  posts_10: B_Posts10,
  posts_30: B_Posts30,
  posts_50: B_Posts50,
  influencer_cookfluencer: B_Influencer,
  rec_first: B_RecFirst,
  rec_5_days_streak: B_RecStreak5,
  rec_cooked_1: B_Cooked1,
  rec_cooked_10: B_Cooked10,
  rec_cooked_50: B_Cooked50,
  ingredients_10_plus: B_Ingredient10,
  weekly_goal_1: B_Goal1,
  weekly_goal_5: B_Goal5,
}

export const LABELS_KO: Record<string, { label: string; group: string }> = {
  // 대회
  first_contest:           { label: '첫 대회!', group: '대회' },
  contest_rank_1:          { label: '최고의 셰프', group: '대회' },
  contests_5:              { label: '꾸준한 경쟁자', group: '대회' },
  contests_10:             { label: '경험 많은 셰프', group: '대회' },
  contests_20:             { label: '경쟁 1인자', group: '대회' },
  contest_rank_top5:       { label: '상위 5위 달성', group: '대회' },
  likes_50_plus:           { label: '좋아요 메이커', group: '대회' },
  posts_10:                { label: '게시자 입문', group: '대회' },
  posts_30:                { label: '게시자 고수', group: '대회' },
  posts_50:                { label: '게시자 장인', group: '대회' },
  influencer_cookfluencer: { label: '쿡플루언서', group: '대회' },
  // 레시피 추천
  rec_first:               { label: '첫 추천', group: '레시피 추천' },
  rec_5_days_streak:       { label: '5일 연속 추천', group: '레시피 추천' },
  rec_cooked_1:            { label: '첫 조리 성공', group: '레시피 추천' },
  rec_cooked_10:           { label: '요리의 즐거움', group: '레시피 추천' },
  rec_cooked_50:           { label: '요리 마스터', group: '레시피 추천' },
  ingredients_10_plus:     { label: '식재료 수집가', group: '레시피 추천' },
  // 목표
  weekly_goal_1:           { label: '첫 주간 목표 달성', group: '목표' },
  weekly_goal_5:           { label: '꾸준한 달성가', group: '목표' },
}

export function BadgeIcon({ code, size = 64, earned = false, label }: { code: string; size?: number; earned?: boolean; label?: string }) {
  const Comp = MAP[code]
  const meta = LABELS_KO[code]
  const lockedStyle = earned ? {} : ({ filter: 'grayscale(1)', opacity: 0.55 } as const)
  if (!Comp) {
    return <span style={{ display: 'inline-block', width: size, height: size, borderRadius: 12, border: '1px solid #e5e7eb', background: '#f3f4f6' }} />
  }
  return (
    <span
      role="img"
      aria-label={label || meta?.label || code}
      title={label || meta?.label || code}
      style={{ display: 'inline-block', width: size, height: size, ...lockedStyle }}
    >
      <Comp />
    </span>
  )
}

export default BadgeIcon
