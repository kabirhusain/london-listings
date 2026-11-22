/** Port of SearchScreen.kt. On phones it's its own screen; on wide screens the results fill the middle column. */
import { useEffect, useMemo, useRef, useState } from 'react'
import { CATEGORY_LABEL } from '../../domain/models'
import * as Q from '../../domain/queries'
import { goBack, navigate } from '../../data/route'
import * as F from '../../text/format'
import { artSeed, headline, isMusic, runLabel } from '../../text/showingText'
import { useApp } from '../context'
import { BackArrowIcon, CloseIcon, NavLink, Poster } from '../components/basics'
import { VenueTimesRow } from '../components/rows'
import { LoadingState, MessageState } from '../components/states'

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

export function SearchResults() {
  const { listings, route, now, feed } = useApp()
  const query = useDebounced((route.q ?? '').trim(), 200)
  const results = useMemo(
    () => (query && listings ? Q.search(listings.showings, query, now) : null),
    [query, listings, now],
  )
  if (!listings) return <LoadingState />
  if (results === null)
    return (
      <MessageState
        title="Find it."
        body="Films, plays, gigs, comedy and dance, by title, venue or performer. Searches everything still to come; your filters don't apply here."
      />
    )
  if (results.length === 0)
    return (
      <MessageState
        title="No match."
        body={`Nothing still to come matches “${query}”. Try fewer words, or part of a name.${feed.complete ? '' : ' Later dates are still loading.'}`}
      />
    )
  return (
    <div>
      <p className="t-tag muted note-line" style={{ margin: 0 }} aria-live="polite">
        {F.count(results.length, 'result')} · Everything still to come · Filters off
        {!feed.complete && ' · Loading later dates…'}
      </p>
      {results.map((r) => (
        <SearchResultEntry key={r.key} result={r} />
      ))}
    </div>
  )
}

function SearchResultEntry({ result: r }: { result: Q.SearchResult }) {
  const { today, wide } = useApp()
  const [all, setAll] = useState(false)
  const lead = r.lead
  const meta = [
    CATEGORY_LABEL[r.category],
    lead.runtimeMinutes !== null && `${lead.runtimeMinutes} min`,
    runLabel(lead, today),
    !lead.isRun && F.count(r.days.length, 'date'),
    !lead.isRun && F.count(r.venueCount, 'venue'),
  ]
    .filter(Boolean)
    .join(' · ')
  const days = all ? r.days : r.days.slice(0, 3)
  return (
    <article className="entry">
      <NavLink to={{ show: lead.id, sel: null }} push={!wide} className="entry-head">
        <span className="entry-head-main">
          <span className="t-cardTitle row-title">{isMusic(lead) ? headline(lead) : r.title}</span>
          <span className="t-tag accent">{meta}</span>
        </span>
        <Poster url={lead.imageUrl} seed={artSeed(lead)} width={36} height={54} />
      </NavLink>
      <div className="result-days">
        {lead.isRun && <VenueTimesRow vt={{ venue: lead.venue, showings: [] }} />}
        {days.map((d) => (
          <div key={d.date} className="result-day">
            <span className="t-legend">{F.relativeDay(d.date, today)}</span>
            {d.venues.map((vt) => (
              <VenueTimesRow key={vt.venue} vt={vt} />
            ))}
          </div>
        ))}
        {r.days.length > 3 && (
          <button className="text-link t-monoLabel" style={{ alignSelf: 'flex-start', marginLeft: -12 }} onClick={() => setAll(!all)}>
            {all ? 'Show fewer' : `Show all ${r.days.length} dates`}
          </button>
        )}
      </div>
    </article>
  )
}

/** Phone: a full screen with its own back bar and a big input. */
export function SearchScreen() {
  const { route } = useApp()
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (!route.q) input.current?.focus()
    // Only when the screen opens, as the app does.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return (
    <div>
      <div className="topbar">
        <button className="icon-btn bare" onClick={() => goBack({ q: null })} aria-label="Back">
          <BackArrowIcon />
        </button>
        <span className="t-wordmark">Search</span>
      </div>
      <form
        className="search-input-row"
        role="search"
        onSubmit={(e) => {
          e.preventDefault()
          input.current?.blur()
        }}
      >
        <input
          ref={input}
          className="search-input"
          type="search"
          enterKeyHint="search"
          autoCapitalize="words"
          autoComplete="off"
          placeholder="Title, venue, performer"
          aria-label="Search titles, venues and performers"
          value={route.q ?? ''}
          onChange={(e) => navigate({ q: e.target.value })}
        />
        {route.q && (
          <button
            type="button"
            className="icon-btn bare"
            aria-label="Clear search"
            onClick={() => {
              navigate({ q: '' })
              input.current?.focus()
            }}
          >
            <CloseIcon />
          </button>
        )}
      </form>
      <hr className="rule-ink search-rule" />
      <SearchResults />
    </div>
  )
}
