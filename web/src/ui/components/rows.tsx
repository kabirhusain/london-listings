/** Ports of ShowingRow.kt, TitleGroupEntry.kt, TimeBands.kt and UpcomingScreen's DateHeader. */
import { useState, type ReactNode } from 'react'
import { CATEGORY_LABEL, TIME_OF_DAY_LABEL, TIMES_OF_DAY, type Showing, type TimeOfDay } from '../../domain/models'
import type { ListingItem, TitleGroup, VenueTimes } from '../../domain/queries'
import { addDays, londonTime } from '../../domain/time'
import * as F from '../../text/format'
import { artSeed, compactSub, headline, isMusic, rowMeta, runLabel, timing } from '../../text/showingText'
import { useApp } from '../context'
import { NavLink, Poster } from './basics'

/** Opens a showing's detail: pushes a history entry on phones; on wide screens it fills the right column. */
function useOpen() {
  const { wide } = useApp()
  return (s: Showing) => ({ to: { show: s.id, sel: null }, push: !wide })
}

function useSelected(s: Showing) {
  const { route, wide } = useApp()
  return wide && route.show === s.id ? 'true' : undefined
}

export function ShowingRow({ showing: s }: { showing: Showing }) {
  const { now } = useApp()
  const open = useOpen()
  const t = timing(s, now)
  const tag =
    t === 'ENDED'
      ? ['Ended', 'muted']
      : t === 'STARTED'
        ? ['Started', 'muted']
        : isMusic(s)
          ? ['Live', 'accent']
          : s.category !== 'FILM'
            ? [CATEGORY_LABEL[s.category], 'accent']
            : null
  const meta = rowMeta(s)
  return (
    <NavLink {...open(s)} className={`row ${t === 'ENDED' ? 'ended' : t === 'STARTED' ? 'started' : ''}`} current={useSelected(s)}>
      <span className="row-time">
        <span className="t-time">{F.time(s.start)}</span>
        {tag && <span className={`t-tag ${tag[1]}`}>{tag[0]}</span>}
      </span>
      <span className="row-main">
        <span className="t-cardTitle row-title">{headline(s)}</span>
        <span className="t-venue">{s.venue}</span>
        {meta && <span className="t-meta muted row-meta">{meta}</span>}
      </span>
      <Poster url={s.imageUrl} seed={artSeed(s)} width={48} height={72} />
    </NavLink>
  )
}

export function CompactShowingRow({ showing: s }: { showing: Showing }) {
  const open = useOpen()
  return (
    <NavLink {...open(s)} className="row compact" current={useSelected(s)}>
      <span className="t-timeCompact">{F.time(s.start)}</span>
      <span className="row-main">
        <span className="t-compactTitle row-title">{headline(s)}</span>
        <span className="t-body muted row-meta">{compactSub(s)}</span>
      </span>
      <Poster url={s.imageUrl} seed={artSeed(s)} width={36} height={54} />
    </NavLink>
  )
}

export function RunRow({ showing: s, compact = false }: { showing: Showing; compact?: boolean }) {
  const { today } = useApp()
  const open = useOpen()
  return (
    <NavLink {...open(s)} className={`row ${compact ? 'compact' : ''}`} current={useSelected(s)}>
      <span className="row-time">
        <span className={compact ? 't-timeCompact' : 't-time'}>RUN</span>
        <span className="t-tag accent">{CATEGORY_LABEL[s.category]}</span>
      </span>
      <span className="row-main">
        <span className={`${compact ? 't-compactTitle' : 't-cardTitle'} row-title`}>{s.title}</span>
        <span className={compact ? 't-body muted' : 't-venue'}>{s.venue}</span>
        <span className="t-meta muted row-meta">{[runLabel(s, today), rowMeta(s)].filter(Boolean).join(' · ')}</span>
      </span>
      <Poster url={s.imageUrl} seed={artSeed(s)} width={compact ? 36 : 48} height={compact ? 54 : 72} />
    </NavLink>
  )
}

export function NowMarker() {
  const { now } = useApp()
  return (
    <div className="now-marker t-legend accent" role="separator" aria-label="Now">
      NOW {F.time(londonTime(now))}
    </div>
  )
}

export function SectionHeading({ title, note }: { title: string; note?: string | null }) {
  return (
    <div className="section-heading">
      <h2 className="t-sectionTitle" style={{ margin: 0 }}>
        {title}
      </h2>
      {note && <span className="t-meta muted caps" style={{ letterSpacing: '0.12em' }}>{note}</span>}
    </div>
  )
}

export function AlsoRunning({ runs, compact = false }: { runs: Showing[]; compact?: boolean }) {
  if (runs.length === 0) return null
  return (
    <>
      <div className="section-runs">
        <SectionHeading title="Also running" note="Times not listed" />
      </div>
      {runs.map((r) => (
        <RunRow key={r.id} showing={r} compact={compact} />
      ))}
    </>
  )
}

/* ---- Time bands (TimeBands.kt) ---- */

/**
 * Band open/closed flips, remembered per band key for the session (the app keeps them in
 * saved state): a key in the set means "the opposite of this band's default".
 */
const toggled = new Set<string>()

export function TimeBanded({
  items,
  keyPrefix,
  collapsedByDefault,
  nowBeforeId,
  row,
}: {
  items: ListingItem[]
  keyPrefix: string
  collapsedByDefault: (band: TimeOfDay, items: ListingItem[]) => boolean
  nowBeforeId?: string | null
  row: (item: ListingItem) => ReactNode
}) {
  const [, force] = useState(0)
  const bands = TIMES_OF_DAY.map((band) => ({ band, items: items.filter((i) => i.showing.timeOfDay === band) })).filter(
    (b) => b.items.length > 0,
  )
  return (
    <>
      {bands.map(({ band, items: bandItems }) => {
        const key = keyPrefix + band
        const collapsed = collapsedByDefault(band, bandItems) !== toggled.has(key)
        return (
          <section key={key} aria-label={TIME_OF_DAY_LABEL[band]}>
            <button
              className="band-head"
              aria-expanded={!collapsed}
              onClick={() => {
                if (toggled.has(key)) toggled.delete(key)
                else toggled.add(key)
                force((n) => n + 1)
              }}
            >
              <span className="t-legend accent">{TIME_OF_DAY_LABEL[band]}</span>
              <span className="t-meta muted range">{F.TIME_RANGE[band]}</span>
              <span className="t-tag muted">{collapsed ? `${bandItems.length} · Tap to open` : bandItems.length}</span>
              <span className="t-timeCompact" aria-hidden="true">
                {collapsed ? '+' : '−'}
              </span>
            </button>
            {!collapsed &&
              bandItems.map((item) => (
                <div key={item.showing.id}>
                  {item.showing.id === nowBeforeId && <NowMarker />}
                  {row(item)}
                </div>
              ))}
          </section>
        )
      })}
    </>
  )
}

/* ---- One entry per title (TitleGroupEntry.kt) ---- */

export function TimePill({ showing: s }: { showing: Showing }) {
  const { now } = useApp()
  const open = useOpen()
  const gone = s.start.ms <= now || s.isSoldOut
  return (
    <NavLink {...open(s)} className={`pill t-timeCompact ${gone ? 'gone' : ''}`} label={`${F.time(s.start)}${s.isSoldOut ? ', sold out' : ''}`}>
      {F.time(s.start)}
    </NavLink>
  )
}

export function VenueTimesRow({ vt }: { vt: VenueTimes }) {
  return (
    <div className="venue-times">
      <span className="t-venue">{vt.venue}</span>
      {vt.showings.length === 0 ? (
        <span className="t-tag muted" style={{ paddingTop: 9 }}>
          Times not listed
        </span>
      ) : (
        <span className="pills">
          {vt.showings.map((s) => (
            <TimePill key={s.id} showing={s} />
          ))}
        </span>
      )}
    </div>
  )
}

export function TitleGroupEntry({ group: g }: { group: TitleGroup }) {
  const { today, route, wide } = useApp()
  const open = useOpen()
  const lead = g.lead
  const image = g.venues.flatMap((v) => v.showings).find((s) => s.imageUrl)?.imageUrl ?? lead.imageUrl
  const meta = [
    CATEGORY_LABEL[g.category],
    lead.runtimeMinutes !== null && `${lead.runtimeMinutes} min`,
    lead.certificate,
    runLabel(lead, today),
    g.venues.length > 1 && `${g.venues.length} venues`,
  ]
    .filter(Boolean)
    .join(' · ')
  const selected = wide && g.venues.some((v) => v.showings.some((s) => s.id === route.show) || (v.showings.length === 0 && lead.id === route.show))
  return (
    <article className={`entry ${g.allStarted ? 'all-started' : ''}`} style={selected ? { background: 'color-mix(in srgb, var(--accent) 9%, transparent)' } : undefined}>
      <NavLink {...open(lead)} className="entry-head">
        <span className="entry-head-main">
          <span className="t-cardTitle row-title">{isMusic(lead) ? headline(lead) : g.title}</span>
          <span className="t-tag accent">{meta}</span>
        </span>
        <Poster url={image} seed={artSeed(lead)} width={36} height={54} />
      </NavLink>
      <div className="entry-venues">
        {g.venues.map((vt) => (
          <VenueTimesRow key={vt.venue} vt={vt} />
        ))}
      </div>
    </article>
  )
}

/* ---- Upcoming's sticky day header ---- */
export function DateHeader({ date, size }: { date: string; size: number }) {
  const { today } = useApp()
  const tomorrow = addDays(today, 1)
  const prefix = date === tomorrow ? 'Tomorrow · ' : date === today ? 'Today · ' : ''
  return (
    <h2 className="date-header" style={{ margin: 0, fontWeight: 'inherit' }}>
      <span className="day">
        <span className="t-dayHeader">{F.dow(date)}</span>
        <span className={`t-dayHeader ${date === tomorrow ? 'accent' : ''}`}>{F.dayNumber(date)}</span>
        <span className="t-dayHeaderMonth muted">{F.month(date)}</span>
      </span>
      <span className="note">
        {prefix}
        {F.count(size, 'showing')}
      </span>
    </h2>
  )
}
