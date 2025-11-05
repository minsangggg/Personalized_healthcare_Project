import api from './axios'

// Use DB column names directly
export type Recipe = {
  recipe_id: number
  recipe_nm_ko: string
  cooking_time?: number | null
  level_nm?: string | null
  ingredient_full?: any
  step_text?: any
}

export type SelectedRecipe = {
  selected_id: number
  recommend_id: number
  recipe_id: number
  recipe_nm_ko: string
  action?: number
  cooking_time?: number
  level_nm?: string
  selected_date: string
}

export type SelectedRecipesResponse = {
  user_id: string
  count: number
  recipes: SelectedRecipe[]
}

// No normalization: API returns DB column names

export const recipeAPI = {
  async recommendTop3(): Promise<Recipe[]> {
    const { data } = await api.get('/me/recommendations')
    const list: any[] = Array.isArray(data)
      ? data
      : (data?.recommended_db_candidates ?? data?.recommended ?? [])
    // recommendations endpoint already returns DB columns
    return (list as Recipe[]).filter(x => Number.isFinite(x.recipe_id))
  },

  async selectRecipe(recipeId: number): Promise<void> {
    await api.post('/me/selected-recipe', { recipe_id: recipeId })
  },

  async getSelected(): Promise<SelectedRecipesResponse> {
    const { data } = await api.get('/recipes/selected')
    return data
  },

  async getRecipe(id: number): Promise<Recipe> {
    const { data } = await api.get(`/recipes/${id}`, { withCredentials: true })
    const raw = data?.recipe ?? data
    return raw as Recipe
  },

  async getRecommendation(recommendId: number): Promise<Recipe> {
    const { data } = await api.get(`/recommendations/${recommendId}`, { withCredentials: true })
    const raw = data?.recommendation ?? data
    // Map to Recipe-like shape (DB column names used in UI):
    return {
      recipe_id: Number(raw.recipe_id),
      recipe_nm_ko: String(raw.recipe_nm_ko ?? ''),
      cooking_time: raw.cooking_time ?? null,
      level_nm: raw.level_nm ?? null,
      ingredient_full: raw.ingredient_full ?? null,
      step_text: raw.step_text ?? null,
    } as Recipe
  },

  async deleteSelected(selectedId: number): Promise<void> {
    await api.delete(`/me/selected-recipe/${selectedId}`)
  },

  async setSelectedAction(selectedId: number, action: 0|1): Promise<void> {
    await api.patch(`/me/selected-recipe/${selectedId}/action`, { action })
  },
}
