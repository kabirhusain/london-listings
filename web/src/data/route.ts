/**
 * Everything on screen lives in the URL's query string, so any view can be shared as a link
 * and opened in a new tab. Query parameters only (no paths), so GitHub Pages needs no tricks.
 *
 *   ?tab=today|evening|upcoming   view=calendar & date=YYYY-MM-DD
 *   q=…                            search (present = search open)
 *   show=<id> & sel=<id>           detail, and the selected showtime when it differs
 *   page=credits
 *   cat=film,music  hide=Venue|Venue  time=evening,late|none  arrange=event
 *
 * Filters are also remembered in this browser (localStorage). A link without filters gets
 * the saved ones; a link with filters applies them and saves them. Like the app, hidden
 * venues are stored rather than shown ones, so new venues appear automatically.
 */
import { useSyncExternalStore } from 'react'
import { DEFAULT_FILTERS, filtersEqual, type Filters, type ListLayout } from '../domain/filters'
import { CATEGORIES, TIMES_OF_DAY, type Category, type TimeOfDay } from '../domain/models'
import { parseDate } from '../domain/time'

export type Tab = 'today' | 'evening' | 'upcoming'
export const TABS: Tab[] = ['today', 'evening', 'upcoming']
export const TAB_LABEL: Record<Tab, string> = { today: 'Today', evening: 'This evening', upcoming: 'Next 14 days' }

export interface Route {
  tab: Tab
  calendar: boolean
  /** Selected calendar day; null means the default (tomorrow). */
  date: string | null
  /** Search query; null when search is closed. */
  q: string | null
  show: string | null
  sel: string | null
  page: 'credits' | null
  filters: Filters
  layout: ListLayout
}

/** What a pushed entry came from, for the detail screen's back label. */
export interface HistoryState {
  pushed?: boolean
  backLabel?: string
}

const STORAGE_KEY = 'london-calling.filters.v1'

function readList(p: URLSearchParams, key: string): string[] | null {
  const v = p.get(key)
  if (v === null) return null
  return v === 'none' || v === '' ? [] : v.split(',').map((x) => x.trim().toUpperCase())
}

export function parseRoute(search: string): Route {
  const p = new URLSearchParams(search)
  const tab = TABS.includes(p.get('tab') as Tab) ? (p.get('tab') as Tab) : 'today'
  const cats = readList(p, 'cat')?.filter((c): c is Category => (CATEGORIES as readonly string[]).includes(c))
  const times = readList(p, 'time')?.filter((t): t is TimeOfDay => (TIMES_OF_DAY as readonly string[]).includes(t))
  const hide = p.get('hide')
  return {
    tab,
    calendar: tab === 'upcoming' && p.get('view') === 'calendar',
    date: parseDate(p.get('date') ?? ''),
    q: p.get('q'),
    show: p.get('show'),
    sel: p.get('sel'),
    page: p.get('page') === 'credits' ? 'credits' : null,
    filters: {
      categories: new Set(cats ?? []),
      hiddenVenues: new Set(hide ? hide.split('|').filter(Boolean) : []),
      timesOfDay: new Set(times ?? TIMES_OF_DAY),
    },
    layout: p.get('arrange') === 'event' ? 'BY_EVENT' : 'BY_TIME',
  }
}

const ORDER = <T extends string>(all: readonly T[], set: ReadonlySet<T>) => all.filter((x) => set.has(x))

export function routeSearch(r: Route): string {
  const p = new URLSearchParams()
  if (r.page) p.set('page', r.page)
  if (r.tab !== 'today') p.set('tab', r.tab)
  if (r.tab === 'upcoming' && r.calendar) {
    p.set('view', 'calendar')
    if (r.date) p.set('date', r.date)
  }
  if (r.q !== null) p.set('q', r.q)
  if (r.show) p.set('show', r.show)
  if (r.show && r.sel && r.sel !== r.show) p.set('sel', r.sel)
  const f = r.filters
  if (f.categories.size) p.set('cat', ORDER(CATEGORIES, f.categories).join(',').toLowerCase())
  if (f.hiddenVenues.size) p.set('hide', [...f.hiddenVenues].sort().join('|'))
  if (!filtersEqual({ ...DEFAULT_FILTERS, timesOfDay: f.timesOfDay }, DEFAULT_FILTERS))
    p.set('time', f.timesOfDay.size ? ORDER(TIMES_OF_DAY, f.timesOfDay).join(',').toLowerCase() : 'none')
  if (r.layout === 'BY_EVENT') p.set('arrange', 'event')
  const s = p.toString()
  return s ? `?${s}` : location.pathname
}

const FILTER_KEYS = ['cat', 'hide', 'time', 'arrange']

interface Saved {
  cat?: string[]
  hide?: string[]
  time?: string[]
  layout?: ListLayout
}

function save(r: Route) {
  try {
    const s: Saved = {
      cat: [...r.filters.categories],
      hide: [...r.filters.hiddenVenues],
      time: [...r.filters.timesOfDay],
      layout: r.layout,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
  } catch {
    /* private mode or storage blocked: filters just aren't remembered */
  }
}

function restore(r: Route): Route {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return r
    const s = JSON.parse(raw) as Saved
    return {
      ...r,
      filters: {
        categories: new Set((s.cat ?? []).filter((c): c is Category => (CATEGORIES as readonly string[]).includes(c))),
        hiddenVenues: new Set((s.hide ?? []).filter((v) => typeof v === 'string')),
        timesOfDay: new Set(
          (s.time ?? TIMES_OF_DAY).filter((t): t is TimeOfDay => (TIMES_OF_DAY as readonly string[]).includes(t)),
        ),
      },
      layout: s.layout === 'BY_EVENT' ? 'BY_EVENT' : 'BY_TIME',
    }
  } catch {
    return r
  }
}

let current: Route = parseRoute(location.search)
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((l) => l())

export function initRoute() {
  const p = new URLSearchParams(location.search)
  if (FILTER_KEYS.some((k) => p.has(k))) save(current)
  else {
    current = restore(current)
    history.replaceState(history.state, '', routeSearch(current))
  }
  window.addEventListener('popstate', () => {
    current = parseRoute(location.search)
    emit()
  })
}

export function navigate(patch: Partial<Route>, opts: { push?: boolean; backLabel?: string } = {}) {
  const next: Route = { ...current, ...patch }
  const url = routeSearch(next)
  if (opts.push) history.pushState({ pushed: true, backLabel: opts.backLabel } satisfies HistoryState, '', url)
  else history.replaceState(history.state, '', url)
  if (patch.filters || patch.layout) save(next)
  current = next
  emit()
}

/** Back from a pushed screen (detail, search, credits); if the page was opened on it, close it in place. */
export function goBack(fallback: Partial<Route>) {
  if ((history.state as HistoryState | null)?.pushed) history.back()
  else navigate(fallback)
}

export function historyBackLabel(): string | undefined {
  return (history.state as HistoryState | null)?.backLabel
}

/** The link for a view, for <a href>: keeps filters so the link opens the same list. */
export function hrefFor(patch: Partial<Route>): string {
  return routeSearch({ ...current, ...patch })
}

export function useRoute(): Route {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => current,
  )
}

export function getRoute(): Route {
  return current
}
