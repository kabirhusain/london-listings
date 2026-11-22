/** Ports of TodayScreen.kt, EveningScreen.kt and UpcomingScreen.kt, plus the per-tab header text (TonightRoot.kt). */
import { useMemo, useState, type ReactNode } from 'react'
import { DEFAULT_FILTERS, isDefault } from '../../domain/filters'
import * as Q from '../../domain/queries'
import { addDays, dayOfWeek, daysBetween } from '../../domain/time'
import { navigate } from '../../data/route'
import * as F from '../../text/format'
import { useApp } from '../context'
import { ArrowIcon, NavLink } from '../components/basics'
import { AlsoRunning, CompactShowingRow, DateHeader, ShowingRow, TimeBanded, TitleGroupEntry } from '../components/rows'
import { FilteredEmpty, Freshness, LoadingState, MessageState, NoSignal } from '../components/states'
import { PosterWall } from '../components/PosterWall'

export interface TabView {
  /** The big display word in the header. */
  word: string
  meta: string[]
  /** The count on the filter sheet's button. */
  sheetCount: number
  content: ReactNode
}

/** Loading → skeleton; no data at all → "No signal."; otherwise the content and the footer. */
function ListBody({ children }: { children: ReactNode }) {
  const { listings, feed } = useApp()
  if (!listings) return feed.loading ? <LoadingState /> : <NoSignal />
  return (
    <>
      {children}
      <Freshness />
    </>
  )
}

export function useTabView(onEditFilters: () => void): TabView {
  const { listings, route, now, today, feed } = useApp()
  const showings = listings?.showings ?? []
  const f = route.filters
  const minute = now
  const loadingMeta = !listings ? ['Updating listings…'] : null

  // ---- Today ----
  const todayDay = useMemo(() => Q.day(showings, f, today, minute), [showings, f, today, minute])
  // ---- This evening ----
  const groups = useMemo(() => (route.tab === 'evening' ? Q.evening(showings, f, minute) : []), [showings, f, minute, route.tab])
  // ---- Next 14 days ----
  const needsLater = !feed.complete && feed.window !== null && feed.window.to < addDays(today, 14)
  const sections = useMemo(
    () => (route.tab === 'upcoming' && !route.calendar ? Q.upcoming(showings, f, minute) : []),
    [showings, f, minute, route.tab, route.calendar],
  )
  // ---- This week (poster wall) ----
  const wall = useMemo(() => (route.tab === 'week' ? Q.week(showings, f, minute) : new Map()), [showings, f, minute, route.tab])
  const needsLaterForWeek = !feed.complete && feed.window !== null && feed.window.to < addDays(today, 6)
  const selected = route.date ?? addDays(today, 1)
  const selectedDay = useMemo(
    () => (route.tab === 'upcoming' && route.calendar ? Q.day(showings, f, selected, minute) : null),
    [showings, f, selected, minute, route.tab, route.calendar],
  )

  if (route.tab === 'evening') {
    return {
      word: 'Tonight',
      meta: [F.numericDate(today), 'From 17:00', ...(loadingMeta ?? [F.count(groups.length, 'title')])],
      sheetCount: groups.reduce((n, g) => n + Math.max(g.count, 1), 0),
      content: (
        <ListBody>
          {groups.length === 0 ? (
            <FilteredEmpty
              unfilteredBody="There's nothing in the listings from 5pm tonight."
              filteredBody="Nothing this evening matches these filters."
              onEdit={onEditFilters}
            />
          ) : (
            groups.map((g) => <TitleGroupEntry key={g.key} group={g} />)
          )}
        </ListBody>
      ),
    }
  }

  if (route.tab === 'week') {
    const tiles = [...wall.values()].flat()
    return {
      word: 'This week',
      meta: [F.dateRange(today, addDays(today, 6)), ...(loadingMeta ?? [F.count(tiles.length, 'title')])],
      sheetCount: tiles.reduce((n, t) => n + Math.max(t.group.count, 1), 0),
      content: (
        <ListBody>
          {needsLaterForWeek ? (
            <LoadingState />
          ) : tiles.length === 0 ? (
            <FilteredEmpty
              unfilteredBody="There's nothing in the listings for the next seven days."
              filteredBody="Nothing this week matches these filters."
              onEdit={onEditFilters}
            />
          ) : (
            <PosterWall wall={wall} />
          )}
        </ListBody>
      ),
    }
  }

  if (route.tab === 'upcoming' && route.calendar) {
    const size = selectedDay ? Q.sectionSize(selectedDay) : 0
    return {
      word: 'Calendar',
      meta: [F.numericDate(selected), ...(loadingMeta ?? [F.count(size, 'showing')])],
      sheetCount: size,
      content: (
        <ListBody>
          <ModeSwitch />
          <Calendar selected={selected} />
          {selectedDay && <CalendarDay day={selectedDay} onEdit={onEditFilters} />}
        </ListBody>
      ),
    }
  }

  if (route.tab === 'upcoming') {
    const total = sections.reduce((n, s) => n + Q.sectionSize(s), 0)
    return {
      word: 'Fortnight',
      meta: [F.dateRange(addDays(today, 1), addDays(today, 14)), ...(loadingMeta ?? [F.count(total, 'showing')])],
      sheetCount: total,
      content: (
        <ListBody>
          <ModeSwitch />
          {needsLater ? (
            <LoadingState />
          ) : sections.length === 0 ? (
            <FilteredEmpty
              unfilteredBody="There's nothing in the listings for the next two weeks yet."
              filteredBody="No showings match these filters in the next 14 days."
              onEdit={onEditFilters}
            />
          ) : (
            sections.map((s) => <DaySectionView key={s.date} section={s} />)
          )}
        </ListBody>
      ),
    }
  }

  // Today
  const size = Q.sectionSize(todayDay)
  const venueCount = new Set([...todayDay.items.map((i) => i.showing.venue), ...todayDay.runs.map((r) => r.venue)]).size
  return {
    word: F.weekday(today),
    meta: [F.numericDate(today), ...(loadingMeta ?? [F.count(size, 'showing'), F.count(venueCount, 'venue')])],
    sheetCount: size,
    content: (
      <ListBody>
        {size === 0 ? (
          <FilteredEmpty
            unfilteredBody="There's nothing in the listings for today. Try the next 14 days."
            filteredBody="No showings match these filters today."
            onEdit={onEditFilters}
          />
        ) : (
          <TodayList day={todayDay} />
        )}
      </ListBody>
    ),
  }
}

function TodayList({ day }: { day: Q.DaySection }) {
  const { route, now } = useApp()
  if (route.layout === 'BY_EVENT') return <>{Q.byEvent(day, now).map((g) => <TitleGroupEntry key={g.key} group={g} />)}</>
  const nowIndex = day.items.findIndex((i) => i.showing.start.ms > now)
  const hasNow = nowIndex > 0
  return (
    <>
      <TimeBanded
        items={day.items}
        keyPrefix="today-"
        nowBeforeId={hasNow ? day.items[nowIndex].showing.id : null}
        collapsedByDefault={(_, items) => hasNow && items.every((i) => i.hasStarted)}
        row={(i) => <ShowingRow showing={i.showing} />}
      />
      <AlsoRunning runs={day.runs} />
    </>
  )
}

/** One day of Next 14 days, or the calendar's selected day: sticky date header, then the listings. */
function DaySectionView({ section }: { section: Q.DaySection }) {
  const { route, now } = useApp()
  return (
    <section>
      <DateHeader date={section.date} size={Q.sectionSize(section)} />
      {route.layout === 'BY_EVENT' ? (
        Q.byEvent(section, now).map((g) => <TitleGroupEntry key={g.key} group={g} />)
      ) : (
        <>
          <TimeBanded
            items={section.items}
            keyPrefix={`${section.date}-`}
            collapsedByDefault={() => false}
            row={(i) => <CompactShowingRow showing={i.showing} />}
          />
          <AlsoRunning runs={section.runs} compact />
        </>
      )}
    </section>
  )
}

function ModeSwitch() {
  const { route } = useApp()
  return (
    <div className="mode-switch t-monoLabel" role="group" aria-label="View">
      <NavLink to={{ calendar: false }} current={!route.calendar ? 'true' : undefined}>
        List
      </NavLink>
      <NavLink to={{ calendar: true }} current={route.calendar ? 'true' : undefined}>
        Calendar
      </NavLink>
    </div>
  )
}

const monthStart = (date: string) => `${date.slice(0, 7)}-01`
const addMonths = (month: string, n: number) => {
  const y = +month.slice(0, 4)
  const m = +month.slice(5, 7) - 1 + n
  return `${y + Math.floor(m / 12)}-${String((((m % 12) + 12) % 12) + 1).padStart(2, '0')}-01`
}

function Calendar({ selected }: { selected: string }) {
  const { listings, route, now, today, feed } = useApp()
  const counts = useMemo(() => Q.calendarCounts(listings?.showings ?? [], route.filters, now), [listings, route.filters, now])
  const first = monthStart(today)
  const lastDate = [...counts.keys()].reduce((a, b) => (b > a ? b : a), today)
  const last = monthStart(lastDate)
  const [shown, setShown] = useState(monthStart(selected))
  const month = shown < first ? first : shown > last ? last : shown
  const daysInMonth = daysBetween(month, addMonths(month, 1))
  const lead = dayOfWeek(month)
  const dates = Array.from({ length: daysInMonth }, (_, i) => addDays(month, i))
  const busiest = Math.max(1, ...dates.map((d) => counts.get(d) ?? 0))
  const cells: (string | null)[] = [...Array(lead).fill(null), ...dates]
  while (cells.length % 7) cells.push(null)
  const pending = !feed.complete && feed.window !== null && addMonths(month, 1) > feed.window.to

  return (
    <div className="calendar">
      <div className="cal-nav">
        <button className="icon-btn" disabled={month <= first} onClick={() => setShown(addMonths(month, -1))} aria-label="Previous month">
          <ArrowIcon size={18} className="flip" />
        </button>
        <h2 className="t-sectionTitle" style={{ margin: 0 }} aria-live="polite">
          {F.monthYear(month)}
        </h2>
        <button className="icon-btn" disabled={month >= last} onClick={() => setShown(addMonths(month, 1))} aria-label="Next month">
          <ArrowIcon size={18} />
        </button>
      </div>
      <div className="cal-grid" role="grid" aria-label={F.monthYear(month)}>
        {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
          <span key={i} className="cal-head t-legend muted" aria-hidden="true">
            {d}
          </span>
        ))}
        {cells.map((d, i) => {
          if (!d) return <span key={`b${i}`} className="cal-blank" />
          const n = counts.get(d) ?? 0
          const enabled = d >= today
          const isSel = d === selected
          const bg = isSel ? undefined : enabled && n > 0 ? `color-mix(in srgb, var(--accent) ${Math.round((0.08 + (0.32 * n) / busiest) * 100)}%, var(--bg))` : undefined
          return (
            <NavLink
              key={d}
              to={{ date: d }}
              className={`cal-cell ${!enabled ? 'disabled' : n === 0 ? 'empty' : ''} ${d === today && !isSel ? 'today' : ''}`}
              style={bg ? { background: bg } : undefined}
              current={isSel ? 'date' : undefined}
              label={`${F.longDay(d)}, ${F.count(n, 'listing')}`}
            >
              <span className="t-toggle">{F.dayNumber(d)}</span>
              {enabled && n > 0 && <span className="t-tag">{n}</span>}
            </NavLink>
          )
        })}
      </div>
      {pending && <p className="t-tag muted" style={{ margin: '6px 0 0' }}>Loading later dates…</p>}
      <div className="rule" style={{ marginTop: 10 }} />
    </div>
  )
}

function CalendarDay({ day, onEdit }: { day: Q.DaySection; onEdit: () => void }) {
  const { route } = useApp()
  if (Q.sectionSize(day) > 0) return <DaySectionView section={day} />
  const defaults = isDefault(route.filters)
  return (
    <>
      <DateHeader date={day.date} size={0} />
      <MessageState
        title={'Nothing\non.'}
        body={defaults ? `There's nothing in the listings for ${F.longDay(day.date)}.` : `Nothing on ${F.longDay(day.date)} matches these filters.`}
        primary={defaults ? undefined : { label: 'Clear filters', onClick: () => navigate({ filters: DEFAULT_FILTERS }) }}
        secondary={defaults ? undefined : { label: 'Edit', onClick: onEdit }}
      />
    </>
  )
}
