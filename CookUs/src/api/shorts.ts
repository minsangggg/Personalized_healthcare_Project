const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '') || ''

export function buildShortsOpenUrl(title: string){
  const base = API_BASE || ''
  const q = encodeURIComponent(title)
  const path = `/shorts/open?title=${q}`
  return base ? `${base}${path}` : path
}

