/**
 * Port of tonight-in-london ui/Format.kt: every display string and date format in one place.
 * Day and month names come from fixed English arrays (as java.time's Locale.UK gives),
 * so output doesn't depend on the browser's locale ("Sep", never "Sept").
 */
import { addDays, dayOfWeek, londonTime, type LondonTime } from '../domain/time'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

const pad = (n: number) => String(n).padStart(2, '0')
const parts = (date: string) => ({ y: +date.slice(0, 4), m: +date.slice(5, 7), d: +date.slice(8, 10) })

/** "19:30", London time. */
export function time(t: LondonTime): string {
  return `${pad(t.hour)}:${pad(t.minute)}`
}

/** "Sunday 22 November" */
export function longDay(date: string): string {
  const { m, d } = parts(date)
  return `${WEEKDAYS[dayOfWeek(date)]} ${d} ${MONTHS[m - 1]}`
}

/** "Sun 22 Nov" */
export function shortDay(date: string): string {
  const { m, d } = parts(date)
  return `${dow(date)} ${d} ${MONTHS[m - 1].slice(0, 3)}`
}

/** "Saturday" */
export function weekday(date: string): string {
  return WEEKDAYS[dayOfWeek(date)]
}

/** "24.10.26" */
export function numericDate(date: string): string {
  const { y, m, d } = parts(date)
  return `${pad(d)}.${pad(m)}.${pad(y % 100)}`
}

/** "25.10 – 07.11" */
export function dateRange(from: string, to: string): string {
  const a = parts(from)
  const b = parts(to)
  return `${pad(a.d)}.${pad(a.m)} – ${pad(b.d)}.${pad(b.m)}`
}

/** "Sat" */
export function dow(date: string): string {
  return WEEKDAYS[dayOfWeek(date)].slice(0, 3)
}

/** "Oct" */
export function month(date: string): string {
  return MONTHS[parts(date).m - 1].slice(0, 3)
}

/** "November 2026" */
export function monthYear(date: string): string {
  const { y, m } = parts(date)
  return `${MONTHS[m - 1]} ${y}`
}

export function dayNumber(date: string): number {
  return parts(date).d
}

/** "Today", "Tomorrow" or "Tue 27 Oct": used on showtime chips. */
export function relativeDay(date: string, today: string): string {
  if (date === today) return 'Today'
  if (date === addDays(today, 1)) return 'Tomorrow'
  return shortDay(date)
}

export function count(n: number, singular: string, plural = `${singular}s`): string {
  return `${n} ${n === 1 ? singular : plural}`
}

/**
 * When the listings were last updated. The app shows when it last downloaded the file; a web
 * page downloads it on every visit, so the site shows when the listings themselves were built.
 */
export function updated(updatedAt: number | null, now: number): string {
  if (updatedAt === null) return 'Not updated yet'
  const minutes = Math.floor((now - updatedAt) / 60_000)
  const local = londonTime(updatedAt)
  if (minutes < 1) return 'Updated just now'
  if (minutes < 60) return `Updated ${minutes} min ago`
  if (local.date === londonTime(now).date) return `Updated at ${time(local)}`
  return `Updated ${shortDay(local.date)}`
}

export type RefreshError = 'OFFLINE' | 'SERVER' | 'BAD_FORMAT'

export function error(e: RefreshError): string {
  switch (e) {
    case 'OFFLINE':
      return 'You appear to be offline.'
    case 'SERVER':
      return "The listings server isn't responding."
    case 'BAD_FORMAT':
      return "The listings file couldn't be read."
  }
}

/** Time-of-day ranges, as on the filter tiles and chips. */
export const TIME_RANGE = { MORNING: '–12', AFTERNOON: '12–17', EVENING: '17–22', LATE: '22+' } as const
