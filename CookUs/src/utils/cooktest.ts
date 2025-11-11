export function extractCookUserId(raw: number | string) {
  const str = String(raw ?? '').trim()
  if (!str) return ''
  const idx = str.lastIndexOf('#')
  return idx >= 0 ? str.slice(idx + 1).trim() : str
}

export function formatCookUserDisplay(_userId: number | string, userName?: string) {
  if (typeof userName === 'string' && userName.trim().length > 0) return userName.trim()
  return '사용자'
}

export function formatCookUserHandle(userId: number | string) {
  const id = extractCookUserId(userId)
  return id ? `#${id}` : '#-'
}
