export type BadgeCategory = '대회' | '레시피 추천' | '목표'

export type BadgeCatalogItem = {
  code: string
  name_ko: string
  category: BadgeCategory
  description: string
  target_value?: number
}

export const badgeCatalog: BadgeCatalogItem[] = [
  { code: 'first_contest', name_ko: '첫 대회!', category: '대회', description: '첫 번째 대회에 참여했습니다.' },
  { code: 'contest_rank_1', name_ko: '최고의 셰프', category: '대회', description: '대회에서 1위를 달성했습니다.' },
  { code: 'contests_5', name_ko: '꾸준한 경쟁자', category: '대회', description: '대회에 5번 이상 참여했습니다.', target_value: 5 },
  { code: 'contests_10', name_ko: '경험 많은 셰프', category: '대회', description: '대회에 10번 이상 참여했습니다.', target_value: 10 },
  { code: 'likes_50_plus', name_ko: '좋아요 메이커', category: '대회', description: '게시글에 50개 이상의 좋아요를 받았습니다.', target_value: 50 },
  { code: 'posts_10', name_ko: '게시글 장인', category: '대회', description: '게시글 10개를 작성했습니다.', target_value: 10 },
  { code: 'rec_first', name_ko: '첫 추천', category: '레시피 추천', description: '첫 번째 레시피 추천을 받았습니다.' },
  { code: 'rec_5_days_streak', name_ko: '5일 연속 추천', category: '레시피 추천', description: '5일 연속 추천을 받았습니다.', target_value: 5 },
  { code: 'rec_cooked_1', name_ko: '첫 조리 성공', category: '레시피 추천', description: '추천 레시피로 첫 조리에 성공했습니다.' },
  { code: 'ingredients_10_plus', name_ko: '재료 도감 수집가', category: '레시피 추천', description: '재료를 10개 이상 추가했습니다.', target_value: 10 },
  { code: 'weekly_goal_1', name_ko: '첫 주간 목표 달성', category: '목표', description: '주간 목표를 처음 달성했습니다.', target_value: 1 },
  { code: 'weekly_goal_5', name_ko: '꾸준한 달성가', category: '목표', description: '주간 목표를 5번 달성했습니다.', target_value: 5 },
]

