import api from './axios'

export type BadgeCategory = 'contest' | 'recipe' | 'goal'

export type EarnedBadge = {
  badge_id: number
  name: string
  category: BadgeCategory
  earned_at: string
  is_active: boolean
}

export type BadgeProgress = {
  current: number
  target: number
  remaining: number
}

export type LockedBadge = {
  badge_id: number
  name: string
  category: BadgeCategory
  progress?: BadgeProgress | null
}

export type BadgeOverview = {
  earned: EarnedBadge[]
  locked: LockedBadge[]
}

export const badgesAPI = {
  async overview(): Promise<BadgeOverview> {
    const { data } = await api.get('/me/badges/overview')
    return data
  },
}

