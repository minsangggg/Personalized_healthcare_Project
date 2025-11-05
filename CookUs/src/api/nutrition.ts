import api from './axios'

export type SupplementIntake = {
  intake_id: number
  user_id: number
  supplement_name: string
  dosage: number
  unit: string
  taken_at: string
}

export type CreateIntakeDto = {
  supplement_name: string
  dosage: number
  unit: string
  taken_at: string
}

export type Recommendation = {
  name: string
  reason: string
}

// TimeSlot is stored as a combined label like "아침-식후" or "저녁-공복"
export type TimeSlot = string

export type SupplementPlan = {
  plan_id: number
  supplement_name: string
  time_slot: TimeSlot
}

export type DayStatus = { date: string; total: number; taken: number }
export type DayPlan = SupplementPlan & { taken: boolean }

export type RecommendFilters = {
  age_band: '10대'|'20대'|'30대'|'40대'|'50대 이상'
  sex: 'F'|'M'
  pregnant_possible?: boolean
  shapes?: string[]
  goals?: string[]
}

export const nutritionAPI = {
  async listIntakes(): Promise<SupplementIntake[]> {
    const { data } = await api.get('/nutrition/supplements')
    if (Array.isArray(data)) return data
    if (Array.isArray((data as any)?.items)) return (data as any).items
    return []
  },
  async addIntake(body: CreateIntakeDto): Promise<SupplementIntake> {
    const { data } = await api.post('/nutrition/supplements', body)
    return data
  },
  async deleteIntake(intakeId: number): Promise<void> {
    await api.delete(`/nutrition/supplements/${intakeId}`)
  },
  async getRecommendations(): Promise<Recommendation[]> {
    const { data } = await api.get('/nutrition/recommendations')
    if (Array.isArray(data)) return data
    if (Array.isArray((data as any)?.items)) return (data as any).items
    return []
  },

  async recommend(filters: RecommendFilters): Promise<{ goal: string; items: Array<{ category: string; product_name: string; function: string; shape: string; timing?: string }> }[]> {
    const { data } = await api.post('/nutrition/recommend', filters)
    return data
  },

  // Plans (for calendar tracking)
  async listPlans(): Promise<SupplementPlan[]> {
    const { data } = await api.get('/nutrition/plans')
    return Array.isArray(data) ? data : []
  },
  async createPlan(name: string, time_slot: TimeSlot): Promise<SupplementPlan> {
    const { data } = await api.post('/nutrition/plans', { supplement_name: name, time_slot })
    return data
  },
  async deletePlan(planId: number): Promise<void> {
    await api.delete(`/nutrition/plans/${planId}`)
  },
  async updatePlan(planId: number, name: string, time_slot: TimeSlot): Promise<SupplementPlan> {
    const { data } = await api.put(`/nutrition/plans/${planId}`, { supplement_name: name, time_slot })
    return data
  },
  async getMonthStatus(ym: string): Promise<DayStatus[]> {
    const { data } = await api.get('/nutrition/calendar', { params: { month: ym } })
    return Array.isArray(data) ? data : []
  },
  async getDaily(date: string): Promise<DayPlan[]> {
    const { data } = await api.get('/nutrition/daily', { params: { date } })
    return Array.isArray(data) ? data : []
  },
  async setTaken(planId: number, date: string, taken: boolean): Promise<void> {
    await api.post('/nutrition/take', { plan_id: planId, date, taken })
  },
}
