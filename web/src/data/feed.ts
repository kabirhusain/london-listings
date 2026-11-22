/**
 * Loads the listings. The website reads the split feed published next to listings.json:
 * data/soon.json (today + ~2 weeks, small) first, so Today, This evening and the next 14 days
 * can draw straight away; then data/later.json in the background for search, the calendar
 * and full showtimes. If the split feed isn't there, it falls back to listings.json.
 *
 * Like the app's ListingsRepository: a failed refresh keeps the listings already shown,
 * and data older than 30 minutes is refreshed when the page comes back into view.
 */
import { useSyncExternalStore } from 'react'
import { mergeListings, parseListingsText, FeedFormatError } from '../domain/parse'
import type { Listings } from '../domain/models'
import type { RefreshError } from '../text/format'

const BASE = (import.meta.env.VITE_FEED_BASE as string | undefined) ?? './'
const STALE_AFTER = 30 * 60_000

export interface FeedState {
  listings: Listings | null
  /** True once everything still to come is loaded (later.json merged, or the full listings.json). */
  complete: boolean
  /** Listing dates covered before `complete`: the soon.json window. */
  window: { from: string; to: string } | null
  loading: boolean
  /** Set when the last load failed; cleared by a successful one. */
  error: RefreshError | null
  /** True when a refresh failed while listings were already shown: the snackbar's message. */
  refreshFailed: boolean
  loadedAt: number | null
}

let state: FeedState = {
  listings: null,
  complete: false,
  window: null,
  loading: true,
  error: null,
  refreshFailed: false,
  loadedAt: null,
}
const listeners = new Set<() => void>()
function set(patch: Partial<FeedState>) {
  state = { ...state, ...patch }
  listeners.forEach((l) => l())
}

class HttpError extends Error {}

async function fetchListings(path: string, fresh: boolean): Promise<{ listings: Listings; window: FeedState['window'] }> {
  let res: Response
  try {
    // 'no-cache' revalidates with the server (ETag), so an unchanged file isn't downloaded again.
    res = await fetch(new URL(path, new URL(BASE, location.href)), { cache: fresh ? 'no-cache' : 'default' })
  } catch {
    throw new TypeError('offline')
  }
  if (!res.ok) throw new HttpError(String(res.status))
  const text = await res.text()
  const listings = parseListingsText(text)
  let window: FeedState['window'] = null
  try {
    const w = (JSON.parse(text) as { window?: { from?: unknown; to?: unknown } }).window
    if (w && typeof w.from === 'string' && typeof w.to === 'string') window = { from: w.from, to: w.to }
  } catch {
    /* parseListingsText already validated it */
  }
  return { listings, window }
}

const errorOf = (e: unknown): RefreshError =>
  e instanceof FeedFormatError ? 'BAD_FORMAT' : e instanceof HttpError ? 'SERVER' : 'OFFLINE'

let inFlight: Promise<void> | null = null

/** Loads (or reloads) the listings. Concurrent calls share the load already running. */
export function load(fresh = false): Promise<void> {
  if (inFlight) return inFlight
  inFlight = (async () => {
    set({ loading: true })
    try {
      let first: Awaited<ReturnType<typeof fetchListings>>
      let split = true
      try {
        first = await fetchListings('data/soon.json', fresh)
      } catch (e) {
        if (e instanceof TypeError) throw e // offline: the fallback won't work either
        split = false
        first = await fetchListings('listings.json', fresh)
      }
      set({
        listings: first.listings,
        window: first.window,
        complete: !split,
        loading: false,
        error: null,
        refreshFailed: false,
        loadedAt: Date.now(),
      })
      if (split) {
        try {
          const later = await fetchListings('data/later.json', fresh)
          set({ listings: mergeListings(first.listings, later.listings), complete: true })
        } catch {
          // Without later.json, search, the calendar and showtimes still work on the next ~2 weeks.
          set({ complete: true })
        }
      }
    } catch (e) {
      set({ loading: false, error: errorOf(e), refreshFailed: state.listings !== null })
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

export function dismissRefreshError() {
  set({ refreshFailed: false })
}

export function refreshIfStale() {
  if (state.loadedAt !== null && Date.now() - state.loadedAt > STALE_AFTER) void load(true)
}

let started = false
export function startFeed() {
  if (started) return
  started = true
  void load()
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') refreshIfStale()
  })
  window.addEventListener('focus', refreshIfStale)
  window.addEventListener('online', () => {
    if (state.error) void load(true)
  })
}

export function useFeed(): FeedState {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => state,
  )
}
