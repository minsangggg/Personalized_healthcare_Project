import api from './axios'

export type Recipe = {
  id: number
  title: string
  cook_time?: number
  difficulty?: string
  ingredients_text?: string | string[]
  steps_text?: string | string[]
  step_tip?: string | string[]
  image_url?: string
}

export type SelectedRecipe = {
  selected_id: number
  recommend_id: number
  recipe_id: number
  title: string
  cooking_time?: number
  difficulty?: string
  selected_date: string
}

export type SelectedRecipesResponse = {
  user_id: string
  count: number
  recipes: SelectedRecipe[]
}

function normalize(r: any): Recipe {
  return {
    id: Number(r?.id ?? r?.recipe_id),
    title: r?.title ?? r?.recipe_nm_ko ?? '',
    cook_time: r?.cook_time ?? r?.cooking_time,
    difficulty: r?.difficulty ?? r?.level_nm,
    ingredients_text: r?.ingredients_text,
    steps_text: r?.steps_text,
    step_tip: r?.step_tip,
    image_url: r?.image_url,
  }
}

export const recipeAPI = {
  async recommendTop3(): Promise<Recipe[]> {
    const { data } = await api.get('/me/recommendations')
    const list: any[] = Array.isArray(data)
      ? data
      : (data?.recommended_db_candidates ?? data?.recommended ?? [])
    return list.map(normalize).filter(x => Number.isFinite(x.id))
  },
  async selectRecipe(recipeId: number): Promise<void> {
    await api.post('/me/selected-recipe', { recipe_id: recipeId })
  },
  async getSelected(userId: string) {
    const { data } = await api.get('/recipes/selected', { params: { user_id: userId } })
    return data
  },
}
