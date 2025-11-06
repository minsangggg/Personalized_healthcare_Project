// Mock badge catalog and user state for frontend-only gallery
export type BadgeCategory = '대회' | '레시피 추천' | '목표'

export type BadgeCatalogItem = {
  code: string
  name_ko: string
  category: BadgeCategory
  description: string
  target_value?: number
}

export type UserBadge = {
  code: string
  awarded_at: string // ISO string
}

export type BadgeProgress = {
  code: string
  current_value: number
  target_value: number
  is_completed: boolean
}

export const badgeCatalog: BadgeCatalogItem[] = [
  { code: 'first_contest', name_ko: '첫 대회!', category: '대회', description: '첫 번째 대회에 참가했습니다.' },
  { code: 'contest_rank_1', name_ko: '최고의 셰프', category: '대회', description: '대회에서 1위를 달성했습니다.' },
  { code: 'contests_5', name_ko: '꾸준한 경쟁자', category: '대회', description: '대회에 5회 이상 참가했습니다.', target_value: 5 },
  { code: 'contests_10', name_ko: '경험 많은 셰프', category: '대회', description: '대회에 10회 이상 참가했습니다.', target_value: 10 },
  { code: 'likes_50_plus', name_ko: '좋아요 메이커', category: '대회', description: '게시글에 50개 이상 좋아요를 받았습니다.', target_value: 50 },
  { code: 'posts_10', name_ko: '게시자 입문', category: '대회', description: '게시글 10개를 작성했습니다.', target_value: 10 },
  { code: 'rec_first', name_ko: '첫 추천', category: '레시피 추천', description: '첫 번째 레시피 추천을 받았습니다.' },
  { code: 'rec_5_days_streak', name_ko: '5일 연속 추천', category: '레시피 추천', description: '5일 연속 추천을 유지했습니다.', target_value: 5 },
  { code: 'rec_cooked_1', name_ko: '첫 조리 성공', category: '레시피 추천', description: '추천 레시피로 첫 조리에 성공했습니다.' },
  { code: 'ingredients_10_plus', name_ko: '식재료 수집가', category: '레시피 추천', description: '식재료를 10개 이상 추가했습니다.', target_value: 10 },
  { code: 'weekly_goal_1', name_ko: '첫 주간 목표 달성', category: '목표', description: '주간 목표를 처음 달성했습니다.', target_value: 1 },
  { code: 'weekly_goal_5', name_ko: '꾸준한 달성가', category: '목표', description: '주간 목표를 5회 달성했습니다.', target_value: 5 },
]

// Mock user state
export const userBadges: UserBadge[] = [
  { code: 'first_contest', awarded_at: '2025-10-03T12:30:00Z' },
  { code: 'posts_10', awarded_at: '2025-10-10T08:00:00Z' },
  { code: 'rec_cooked_1', awarded_at: '2025-10-18T09:45:00Z' },
]

export const userProgress: BadgeProgress[] = [
  { code: 'contests_5', current_value: 3, target_value: 5, is_completed: false },
  { code: 'contests_10', current_value: 4, target_value: 10, is_completed: false },
  { code: 'likes_50_plus', current_value: 22, target_value: 50, is_completed: false },
  { code: 'rec_5_days_streak', current_value: 2, target_value: 5, is_completed: false },
  { code: 'ingredients_10_plus', current_value: 7, target_value: 10, is_completed: false },
  { code: 'weekly_goal_5', current_value: 1, target_value: 5, is_completed: false },
]

