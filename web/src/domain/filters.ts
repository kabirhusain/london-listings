/** Port of tonight-in-london domain/Filters.kt. */
import { TIMES_OF_DAY, type Category, type Showing, type TimeOfDay } from './models'

export interface Filters {
  /** Categories to show; empty means all of them. */
  categories: ReadonlySet<Category>
  /** Stored as hidden rather than shown so venues added to the feed later appear by default. */
  hiddenVenues: ReadonlySet<string>
  timesOfDay: ReadonlySet<TimeOfDay>
}

export const DEFAULT_FILTERS: Filters = {
  categories: new Set(),
  hiddenVenues: new Set(),
  timesOfDay: new Set(TIMES_OF_DAY),
}

function sameSet<T>(a: ReadonlySet<T>, b: ReadonlySet<T>): boolean {
  if (a.size !== b.size) return false
  for (const x of a) if (!b.has(x)) return false
  return true
}

export function categoriesDefault(f: Filters): boolean {
  return f.categories.size === 0
}
export function venuesDefault(f: Filters): boolean {
  return f.hiddenVenues.size === 0
}
export function timesDefault(f: Filters): boolean {
  return sameSet(f.timesOfDay, DEFAULT_FILTERS.timesOfDay)
}
export function isDefault(f: Filters): boolean {
  return categoriesDefault(f) && venuesDefault(f) && timesDefault(f)
}
export function filtersEqual(a: Filters, b: Filters): boolean {
  return sameSet(a.categories, b.categories) && sameSet(a.hiddenVenues, b.hiddenVenues) && sameSet(a.timesOfDay, b.timesOfDay)
}

export function includesCategory(f: Filters, c: Category): boolean {
  return f.categories.size === 0 || f.categories.has(c)
}

/** Runs have no start time, so the time-of-day filter doesn't apply to them. */
export function matches(f: Filters, s: Showing): boolean {
  return includesCategory(f, s.category) && !f.hiddenVenues.has(s.venue) && (s.isRun || f.timesOfDay.has(s.timeOfDay))
}

/** How Today and Next 14 days are arranged: one row per performance, or one entry per title. */
export type ListLayout = 'BY_TIME' | 'BY_EVENT'

export function makeFilters(p: Partial<Filters>): Filters {
  return { ...DEFAULT_FILTERS, ...p }
}
