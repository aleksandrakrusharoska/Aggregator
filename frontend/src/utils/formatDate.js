const MONTHS_MK = [
  'Јануари', 'Февруари', 'Март', 'Април', 'Мај', 'Јуни',
  'Јули', 'Август', 'Септември', 'Октомври', 'Ноември', 'Декември',
]

export function formatDate(dateStr) {
  if (!dateStr) return null
  const date = new Date(dateStr)
  if (isNaN(date)) return null

  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const dateStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.round((todayStart - dateStart) / 86_400_000)

  if (diffDays === 0) return 'Денес'
  if (diffDays === 1) return 'Вчера'
  if (diffDays === 2) return 'Пред 2 дена'

  return `${date.getDate()} ${MONTHS_MK[date.getMonth()]} ${date.getFullYear()}`
}
