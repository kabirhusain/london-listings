/** Port of tonight-in-london domain/ListingQueries.kt: pure functions over the listings. */
import { matches, type Filters } from './filters'
import { normaliseForSearch, runsOn, type Category, type Showing } from './models'
import { addDays, listingDateOf } from './time'

export interface ListingItem {
  showing: Showing
  hasStarted: boolean
}

/** One day's performances in time order, plus runs (no listed times) that are on that day. */
export interface DaySection {
  date: string
  items: ListingItem[]
  runs: Showing[]
}
export const sectionSize = (d: DaySection) => d.items.length + d.runs.length

export interface Venue {
  name: string
  categories: Set<Category>
}

/** One venue's times for a title in the This evening view. */
export interface VenueTimes {
  venue: string
  showings: Showing[]
}

/**
 * Everything under one title in a stretch of time (e.g. one film at eleven cinemas this evening).
 * venues is ordered by each venue's first time; a run has a single venue with no times.
 */
export interface TitleGroup {
  key: string
  category: Category
  title: string
  /** The next showing that hasn't started, or the last one if all have; opens the detail screen. */
  lead: Showing
  venues: VenueTimes[]
  count: number
  allStarted: boolean
}

/** One day of a search result: that day's venues and times. */
export interface DayVenues {
  date: string
  venues: VenueTimes[]
}

/** A search hit: one title, with its remaining dates collated by day. Runs have no days. */
export interface SearchResult {
  key: string
  category: Category
  title: string
  lead: Showing
  days: DayVenues[]
  count: number
  venueCount: number
}

/** Evening starts at 5pm, matching TimeOfDay EVENING; it runs until the day rolls over. */
export const EVENING_START_HOUR = 17

const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0)
export const chronological = (a: Showing, b: Showing) =>
  a.start.ms - b.start.ms || cmp(a.venue, b.venue) || cmp(a.title, b.title)
const byTitle = (a: Showing, b: Showing) => cmp(a.title, b.title)

function groupBy<T, K>(items: T[], key: (t: T) => K): Map<K, T[]> {
  const m = new Map<K, T[]>()
  for (const it of items) {
    const k = key(it)
    const list = m.get(k)
    if (list) list.push(it)
    else m.set(k, [it])
  }
  return m
}

const venueTimes = (shows: Showing[]): VenueTimes[] =>
  [...groupBy(shows, (s) => s.venue)].map(([venue, showings]) => ({ venue, showings }))

export function today(showings: Showing[], filters: Filters, now: number): ListingItem[] {
  return day(showings, filters, listingDateOf(now), now).items
}

/** A single day's listings: timed performances and the runs on that day. */
export function day(showings: Showing[], filters: Filters, date: string, now: number): DaySection {
  const matching = showings.filter((s) => matches(filters, s))
  return {
    date,
    items: matching
      .filter((s) => !s.isRun && s.listingDate === date)
      .sort(chronological)
      .map((s) => ({ showing: s, hasStarted: s.start.ms <= now })),
    runs: matching.filter((s) => runsOn(s, date)).sort(byTitle),
  }
}

/** The [days] days after today, grouped by date. Days with nothing on are omitted. */
export function upcoming(showings: Showing[], filters: Filters, now: number, days = 14): DaySection[] {
  const todayDate = listingDateOf(now)
  const last = addDays(todayDate, days)
  const matching = showings.filter((s) => matches(filters, s))
  const runs = matching.filter((s) => s.isRun)
  const byDate = groupBy(
    matching.filter((s) => !s.isRun && s.listingDate > todayDate && s.listingDate <= last).sort(chronological),
    (s) => s.listingDate,
  )
  const out: DaySection[] = []
  for (let i = 1; i <= days; i++) {
    const date = addDays(todayDate, i)
    const section: DaySection = {
      date,
      items: (byDate.get(date) ?? []).map((s) => ({ showing: s, hasStarted: false })),
      runs: runs.filter((s) => runsOn(s, date)).sort(byTitle),
    }
    if (sectionSize(section) > 0) out.push(section)
  }
  return out
}

/** Number of matching entries per day from today onwards, for the calendar. Runs count on each day they're on. */
export function calendarCounts(showings: Showing[], filters: Filters, now: number): Map<string, number> {
  const todayDate = listingDateOf(now)
  const counts = new Map<string, number>()
  const bump = (d: string) => counts.set(d, (counts.get(d) ?? 0) + 1)
  for (const s of showings) {
    if (!matches(filters, s)) continue
    if (s.isRun) {
      for (let d = s.listingDate > todayDate ? s.listingDate : todayDate; d <= s.runEnd!; d = addDays(d, 1)) bump(d)
    } else if (s.listingDate >= todayDate) {
      bump(s.listingDate)
    }
  }
  return counts
}

/**
 * Tonight from 5pm, one entry per title with its venues and times underneath. Titles still
 * to come are listed first, by their next start time; runs come after the timed titles.
 */
export function evening(showings: Showing[], filters: Filters, now: number): TitleGroup[] {
  const todayDate = listingDateOf(now)
  const timed = showings.filter(
    (s) =>
      !s.isRun &&
      s.listingDate === todayDate &&
      matches(filters, s) &&
      (s.timeOfDay === 'EVENING' || s.timeOfDay === 'LATE'),
  )
  const runs = showings.filter((s) => runsOn(s, todayDate) && matches(filters, s)).sort(byTitle)
  return groupByTitle(timed, runs, now)
}

/** A day's listings arranged one entry per title ("By event"), in the same order as This evening. */
export function byEvent(d: DaySection, now: number): TitleGroup[] {
  return groupByTitle(
    d.items.map((i) => i.showing),
    d.runs,
    now,
  )
}

/**
 * Groups performances by title (category + match_key). Titles still to come come first, by
 * next start time, then runs, then titles whose performances have all started.
 */
export function groupByTitle(timed: Showing[], runs: Showing[], now: number): TitleGroup[] {
  const groups: TitleGroup[] = [...groupBy(timed, (s) => `${s.category}:${s.matchKey}`)].map(([key, items]) => {
    const sorted = [...items].sort(chronological)
    const next = sorted.find((s) => s.start.ms > now)
    return {
      key,
      category: sorted[0].category,
      title: (next ?? sorted[0]).title,
      lead: next ?? sorted[sorted.length - 1],
      venues: venueTimes(sorted),
      count: sorted.length,
      allStarted: next === undefined,
    }
  })
  groups.sort(
    (a, b) => Number(a.allStarted) - Number(b.allStarted) || a.lead.start.ms - b.lead.start.ms || cmp(a.title, b.title),
  )
  const runGroups: TitleGroup[] = runs.map((s) => ({
    key: `run:${s.id}`,
    category: s.category,
    title: s.title,
    lead: s,
    venues: [{ venue: s.venue, showings: [] }],
    count: 0,
    allStarted: false,
  }))
  return [...groups.filter((g) => !g.allStarted), ...runGroups, ...groups.filter((g) => g.allStarted)]
}

/**
 * Searches everything still to come (filters don't apply): titles, venues and performers.
 * Every word of the query must match somewhere, ignoring case, accents and punctuation.
 * Results are one per title with dates collated by day; title matches rank above
 * venue or performer matches, then sooner before later.
 */
export function search(showings: Showing[], query: string, now: number, limit = 60): SearchResult[] {
  const words = normaliseForSearch(query)
    .split(' ')
    .filter((w) => w.length > 0)
  if (words.length === 0) return []
  const todayDate = listingDateOf(now)
  const hits = showings.filter((s) => {
    const still = s.isRun ? s.runEnd! >= todayDate : s.start.ms > now
    return still && words.every((w) => s.searchText.includes(w))
  })
  const phrase = words.join(' ')
  const rank = (r: SearchResult) => {
    const t = normaliseForSearch(r.title)
    return t.startsWith(phrase) ? 0 : words.every((w) => t.includes(w)) ? 1 : 2
  }
  const results = [...groupBy(hits, (s) => (s.isRun ? `run:${s.id}` : `${s.category}:${s.matchKey}`))].map(
    ([key, items]): SearchResult => {
      const sorted = [...items].sort(chronological)
      const lead = sorted[0]
      return {
        key,
        category: lead.category,
        title: lead.title,
        lead,
        days: lead.isRun
          ? []
          : [...groupBy(sorted, (s) => s.listingDate)].map(([date, shows]) => ({ date, venues: venueTimes(shows) })),
        count: sorted.length,
        venueCount: new Set(sorted.map((s) => s.venue)).size,
      }
    },
  )
  return results
    .map((r) => ({ r, k: rank(r) }))
    .sort((a, b) => a.k - b.k || a.r.lead.start.ms - b.r.lead.start.ms)
    .map((x) => x.r)
    .slice(0, limit)
}

/**
 * Every remaining performance of the same title in the same category at any venue,
 * ignoring the user's filters. Used for films, plays, comedy and dance.
 */
export function showtimes(showings: Showing[], selected: Showing, now: number): DaySection[] {
  const shows = showings
    .filter((s) => !s.isRun && s.category === selected.category && s.matchKey === selected.matchKey)
    .filter((s) => s.start.ms > now || s.id === selected.id)
    .sort(chronological)
  return [...groupBy(shows, (s) => s.listingDate)].map(([date, items]) => ({
    date,
    items: items.map((s) => ({ showing: s, hasStarted: s.start.ms <= now })),
    runs: [],
  }))
}

export function venues(showings: Showing[]): Venue[] {
  const sortKey = (n: string) => n.toLowerCase().replace(/^the /, '')
  return [...groupBy(showings, (s) => s.venue)]
    .map(([name, items]) => ({ name, categories: new Set(items.map((s) => s.category)) }))
    .sort((a, b) => cmp(sortKey(a.name), sortKey(b.name)))
}
