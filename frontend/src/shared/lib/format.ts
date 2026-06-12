const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few
  return many
}

/** The API returns naive-UTC datetimes without a zone suffix. */
export function parseApiDate(value: string): Date {
  const hasZone = /Z$|[+-]\d\d:\d\d$/.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

export function formatRelativeDate(value: string, now: Date = new Date()): string {
  const date = parseApiDate(value)
  const diff = now.getTime() - date.getTime()
  if (diff < MINUTE) return 'только что'
  if (diff < HOUR) {
    const m = Math.floor(diff / MINUTE)
    return `${m} ${plural(m, 'минуту', 'минуты', 'минут')} назад`
  }
  if (diff < DAY) {
    const h = Math.floor(diff / HOUR)
    return `${h} ${plural(h, 'час', 'часа', 'часов')} назад`
  }
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function initialOf(name: string): string {
  return name.trim().charAt(0).toUpperCase() || '?'
}

export function fullName(user: { first_name: string; last_name: string }): string {
  return `${user.first_name} ${user.last_name}`.trim()
}
