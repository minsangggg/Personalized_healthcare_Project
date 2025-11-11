import api from './axios'

export type BadgeCategory = 'contest' | 'recipe' | 'goal' | 'likes' | 'cooked' | 'fridge' | 'ranks' | 'others'

export type EarnedBadge = {
  badge_id: number
  name: string
  category: BadgeCategory
  earned_at: string
  is_active: boolean
  is_displayed: boolean
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
  async setDisplayBadge(badge_id: number | null): Promise<void> {
    if (badge_id == null) {
      await api.delete('/me/badges/title')
    } else {
      await api.post('/me/badges/title', { badge_id })
    }
  },
}

