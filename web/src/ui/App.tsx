import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { listingDateOf } from '../domain/time'
import { useFeed } from '../data/feed'
import { useClock, useMediaQuery, WIDE } from '../data/hooks'
import { navigate, TAB_LABEL, TABS, useRoute, type Route } from '../data/route'
import { Ctx, useApp, type AppCtx } from './context'
import { FitText, NavLink, SearchIcon, SlidersIcon } from './components/basics'
import { FilterRail, FilterSheet } from './components/FilterPanel'
import { activeFilterGroups, Snackbar } from './components/states'
import { CreditsScreen } from './screens/CreditsScreen'
import { DetailScreen } from './screens/DetailScreen'
import { useTabView, type TabView } from './screens/lists'
import { SearchResults, SearchScreen } from './screens/SearchScreen'

function backLabelFor(r: Route): string {
  if (r.q !== null) return 'Search'
  if (r.tab === 'upcoming') return r.calendar ? 'Calendar' : 'Next 14 days'
  if (r.tab === 'week') return 'This week'
  return r.tab === 'evening' ? 'This evening' : 'Today'
}

export function App() {
  const feed = useFeed()
  const route = useRoute()
  const now = useClock()
  const wide = useMediaQuery(WIDE)
  const listings = feed.listings
  const sources = useMemo(() => new Map((listings?.sources ?? []).map((s) => [s.venue, s])), [listings])
  const ctx: AppCtx = {
    now,
    today: listingDateOf(now),
    feed,
    listings,
    route,
    wide,
    sources,
    backLabel: backLabelFor(route),
  }

  useEffect(() => {
    const parts = route.page === 'credits' ? ['Credits'] : route.show ? [listings?.showings.find((s) => s.id === route.show)?.title] : []
    document.title = [...parts.filter(Boolean), 'London Calling'].join(' · ')
  }, [route.page, route.show, listings])

  return (
    <Ctx.Provider value={ctx}>
      {wide ? <WideLayout /> : <PhoneLayout />}
      <Snackbar />
    </Ctx.Provider>
  )
}

/* ---- Shared pieces ---- */

function Tabs() {
  const { route, feed, listings } = useApp()
  return (
    <div className="tabs-wrap">
      <nav className="tabs" aria-label="Listings">
        {TABS.map((t) => (
          <NavLink key={t} to={{ tab: t, calendar: t === 'upcoming' ? route.calendar : false }} className="tab t-tab" current={route.tab === t ? 'page' : undefined}>
            {TAB_LABEL[t]}
          </NavLink>
        ))}
      </nav>
      <div className="rule" />
      <div className={`progress ${feed.loading || (listings && !feed.complete) ? 'active' : ''}`} aria-hidden="true" />
    </div>
  )
}

function HeaderMeta({ view }: { view: TabView }) {
  return (
    <div className="header-meta" aria-live="polite">
      {view.meta.map((m) => (
        <span key={m}>{m}</span>
      ))}
    </div>
  )
}

/** Remembers each view's scroll position, so Back from a detail returns to the same place in the list. */
function useScrollMemory(key: string, scroller: () => HTMLElement | Window | null) {
  const positions = useRef(new Map<string, number>())
  const last = useRef({ key, y: 0 })
  useEffect(() => {
    const el = scroller()
    if (!el) return
    const onScroll = () => {
      last.current.y = el instanceof Window ? el.scrollY : el.scrollTop
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  })
  useLayoutEffect(() => {
    if (last.current.key === key) return
    positions.current.set(last.current.key, last.current.y)
    last.current = { key, y: positions.current.get(key) ?? 0 }
    const el = scroller()
    const y = last.current.y
    if (el instanceof Window) el.scrollTo(0, y)
    else el?.scrollTo(0, y)
  }, [key, scroller])
}

/* ---- Phone (< 900px): the app's single column ---- */

function PhoneLayout() {
  const { route } = useApp()
  const [sheet, setSheet] = useState(false)
  const openSheet = useCallback(() => setSheet(true), [])
  const closeSheet = useCallback(() => setSheet(false), [])
  const view = useTabView(openSheet)
  const screen = route.show ? `show:${route.show}` : route.page ? 'credits' : route.q !== null ? 'search' : `${route.tab}:${route.calendar}:${route.date}`
  useScrollMemory(screen, useCallback(() => window, []))

  if (route.show) return <DetailScreen />
  if (route.page === 'credits') return <CreditsScreen />
  if (route.q !== null) return <SearchScreen />

  const active = activeFilterGroups(route.filters)
  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <NavLink to={{ tab: 'today', calendar: false }} className="t-wordmark">
            London Calling
          </NavLink>
          <button className="icon-btn" onClick={() => navigate({ q: '' }, { push: true })} aria-label="Search">
            <SearchIcon />
          </button>
          <button className={`filters-btn t-monoLabel ${active ? 'active' : ''}`} onClick={openSheet} aria-haspopup="dialog">
            <SlidersIcon />
            {active ? `Filters · ${active}` : 'Filters'}
          </button>
        </div>
        <div className="header-title">
          <FitText text={view.word} className="t-display" maxSize={84} lineHeight={0.84} />
          <HeaderMeta view={view} />
        </div>
      </header>
      <Tabs />
      <main>{view.content}</main>
      {sheet && <FilterSheet count={view.sheetCount} onClose={closeSheet} />}
    </div>
  )
}

/* ---- Wide (≥ 900px): filters | list | detail ---- */

function WideLayout() {
  const { route, feed } = useApp()
  const view = useTabView(() => document.querySelector<HTMLElement>('.rail button')?.focus())
  const search = useRef<HTMLInputElement>(null)
  const main = useRef<HTMLElement>(null)
  const searching = !!route.q && route.q.trim() !== ''
  const mainKey = route.page ? 'credits' : searching ? 'search' : `${route.tab}:${route.calendar}:${route.date}`
  useScrollMemory(mainKey, useCallback(() => main.current, []))

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === '/' && !typing) {
        e.preventDefault()
        search.current?.focus()
      } else if (e.key === 'Escape') {
        if (typing && route.q) navigate({ q: null })
        else if (route.show) navigate({ show: null, sel: null })
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [route.q, route.show])

  // The poster wall takes the detail column's space too until a poster is picked.
  const wallOnly = route.tab === 'week' && !route.show && !route.page && !searching
  return (
    <div className={`wide ${wallOnly ? 'no-side' : ''}`}>
      <header className="wide-top">
        <NavLink to={{ tab: 'today', calendar: false, q: null, page: null }} className="t-wordmark">
          London Calling
        </NavLink>
        <form className="wide-search" role="search" onSubmit={(e) => e.preventDefault()}>
          <SearchIcon />
          <input
            ref={search}
            type="search"
            placeholder="Search title, venue, performer"
            aria-label="Search titles, venues and performers"
            value={route.q ?? ''}
            onChange={(e) => navigate({ q: e.target.value === '' ? null : e.target.value, page: null })}
            autoComplete="off"
          />
          <kbd aria-hidden="true">/</kbd>
        </form>
        <nav className="t-monoLabel" aria-label="About">
          <NavLink to={{ page: 'credits', q: null }} className="text-link" current={route.page ? 'page' : undefined}>
            Credits
          </NavLink>
          <a className="text-link" href="status.html">
            Status
          </a>
        </nav>
      </header>

      <aside className="rail">
        <div className="rail-title">
          <FitText text={view.word} className="t-display" maxSize={84} lineHeight={0.84} />
          <HeaderMeta view={view} />
        </div>
        <FilterRail />
      </aside>

      <main className="main" ref={main}>
        {route.page === 'credits' ? (
          <CreditsScreen />
        ) : searching ? (
          <>
            <div className="tabs-wrap" style={{ padding: '14px var(--gutter) 10px', display: 'flex', alignItems: 'center' }}>
              <span className="t-legend muted" style={{ flex: 1 }}>
                Search: “{route.q!.trim()}”
              </span>
              <button className="text-link t-monoLabel" onClick={() => navigate({ q: null })}>
                Back to listings
              </button>
            </div>
            <div className="rule" />
            <SearchResults />
          </>
        ) : (
          <>
            <Tabs />
            {view.content}
          </>
        )}
      </main>

      <section className="side" aria-label="Details" hidden={wallOnly}>
        {route.show ? (
          <DetailScreen key={route.show} />
        ) : (
          <div className="side-empty">
            <span className="t-sectionTitle">Pick something</span>
            <span className="t-monoBody muted">Choose a showing to see its times, details and where to book.</span>
            {feed.listings && !feed.complete && <span className="t-tag muted">Loading later dates…</span>}
          </div>
        )}
      </section>
    </div>
  )
}
