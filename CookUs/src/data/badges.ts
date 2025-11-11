export type BadgeCategoryKey = 'contest' | 'ranks' | 'likes' | 'recipe' | 'cooked' | 'fridge' | 'goal' | 'others'

export type BadgeMeta = {
  id: number
  iconCode?: string
  category: BadgeCategoryKey
  description?: string
  target?: number
}

export const badgeCategoryLabels: Record<BadgeCategoryKey, string> = {
  contest: '대회',
  ranks: '대회 순위',
  likes: '좋아요',
  recipe: '레시피 추천',
  cooked: '조리',
  fridge: '냉장고',
  goal: '목표',
  others: '기타',
}

export const badgeMetaById: Record<number, BadgeMeta> = {
  1: { id: 1, iconCode: 'first_contest', category: 'contest', description: '대회 첫 참가', target: 1 },
  2: { id: 2, iconCode: 'contest_rank_1', category: 'ranks', description: '대회 1등', target: 1 },
  3: { id: 3, iconCode: 'contests_5', category: 'contest', description: '대회 5번 참가', target: 5 },
  4: { id: 4, iconCode: 'contests_10', category: 'contest', description: '대회 10번 참가', target: 10 },
  5: { id: 5, iconCode: 'contests_20', category: 'contest', description: '대회 20번 참가', target: 20 },
  6: { id: 6, iconCode: 'contest_rank_top5', category: 'ranks', description: '대회 순위권 (1~5등)', target: 5 },
  7: { id: 7, iconCode: 'likes_50_plus', category: 'likes', description: '게시글 좋아요 50개 이상', target: 50 },
  8: { id: 8, iconCode: 'posts_10', category: 'contest', description: '게시글 10개 작성', target: 10 },
  9: { id: 9, iconCode: 'posts_30', category: 'contest', description: '게시글 30개 작성', target: 30 },
 10: { id: 10, iconCode: 'posts_50', category: 'contest', description: '게시글 50개 작성', target: 50 },
 11: { id: 11, iconCode: 'influencer_cookfluencer', category: 'contest', description: '대회 5회 이상 참가 + 순위권 달성', target: 5 },
 12: { id: 12, iconCode: 'rec_first', category: 'recipe', description: '추천받기 기능 첫 사용', target: 1 },
 13: { id: 13, iconCode: 'rec_5_days_streak', category: 'recipe', description: '연속 5일 추천 받기', target: 5 },
 14: { id: 14, iconCode: 'rec_cooked_1', category: 'cooked', description: '조리 완료 1회', target: 1 },
 15: { id: 15, iconCode: 'rec_cooked_10', category: 'cooked', description: '조리 완료 10회', target: 10 },
 16: { id: 16, iconCode: 'rec_cooked_50', category: 'cooked', description: '조리 완료 50회', target: 50 },
 17: { id: 17, iconCode: 'ingredients_10_plus', category: 'fridge', description: '냉장고 재료 10개 이상 등록', target: 10 },
 18: { id: 18, iconCode: 'weekly_goal_1', category: 'goal', description: '주간 목표 첫 달성', target: 1 },
 19: { id: 19, iconCode: 'weekly_goal_5', category: 'goal', description: '주간 목표 5회 달성', target: 5 },
}

export const badgeDisplayOrder = Object.keys(badgeMetaById)
  .map(id => Number(id))
  .sort((a, b) => a - b)
