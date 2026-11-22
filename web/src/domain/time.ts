/**
 * London time without a timezone library. The UK rule (BST from 01:00 UTC on the last
 * Sunday of March to 01:00 UTC on the last Sunday of October) is computed directly,
 * so results don't depend on the visitor's own timezone or on Intl.
 *
 * Dates are ISO strings ("2026-11-22"); date arithmetic is done in UTC.
 */

const HOUR = 3_600_000
const DAY = 24 * HOUR

/** Events before this hour count towards the previous evening (DAY_ROLLOVER_HOUR in the app). */
export const DAY_ROLLOVER_HOUR = 5

function lastSundayUtc(year: number, month: number): number {
  const lastDay = Date.UTC(year, month + 1, 0)
  return lastDay - new Date(lastDay).getUTCDay() * DAY
}

/** London's offset from UTC at an instant, in ms: 0 (GMT) or one hour (BST). */
export function londonOffset(ms: number): number {
  const year = new Date(ms).getUTCFullYear()
  const start = lastSundayUtc(year, 2) + HOUR
  const end = lastSundayUtc(year, 9) + HOUR
  return ms >= start && ms < end ? HOUR : 0
}

/** A moment, with its London wall-clock fields precomputed. */
export interface LondonTime {
  ms: number
  /** London calendar date, "YYYY-MM-DD". */
  date: string
  hour: number
  minute: number
}

export function londonTime(ms: number): LondonTime {
  const wall = new Date(ms + londonOffset(ms))
  return {
    ms,
    date: wall.toISOString().slice(0, 10),
    hour: wall.getUTCHours(),
    minute: wall.getUTCMinutes(),
  }
}

/** Parses an ISO 8601 date-time with an offset ("2026-10-25T19:30:00+00:00"); null if it isn't one. */
export function parseInstant(iso: string): LondonTime | null {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/.test(iso)) return null
  const ms = Date.parse(iso)
  return Number.isNaN(ms) ? null : londonTime(ms)
}

/** "2026-10-31" → itself, if it's a real date; null otherwise. */
export function parseDate(text: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return null
  const ms = Date.parse(`${text}T00:00:00Z`)
  return Number.isNaN(ms) || new Date(ms).toISOString().slice(0, 10) !== text ? null : text
}

/** The listings day an instant belongs to: 5 hours earlier, in London. */
export function listingDateOf(ms: number): string {
  return londonTime(ms - DAY_ROLLOVER_HOUR * HOUR).date
}

export function addDays(date: string, days: number): string {
  return new Date(Date.parse(`${date}T00:00:00Z`) + days * DAY).toISOString().slice(0, 10)
}

/** 0 = Monday … 6 = Sunday (ISO order, as java.time's DayOfWeek). */
export function dayOfWeek(date: string): number {
  return (new Date(`${date}T00:00:00Z`).getUTCDay() + 6) % 7
}

export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / DAY)
}

export const MINUTE = 60_000
