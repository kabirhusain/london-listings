/** Port of tonight-in-london app/src/test/.../domain/ListingQueriesTest.kt, plus web-only cases. */
import { describe, expect, it } from 'vitest'
import { DEFAULT_FILTERS, makeFilters } from './filters'
import { makeShowing, normaliseForSearch, timeOfDayOf, type Category } from './models'
import * as Q from './queries'
import { listingDateOf, parseInstant } from './time'

const at = (s: string) => parseInstant(s)!

function showing(
  id: string,
  start: string,
  o: { category?: Category; venue?: string; matchKey?: string; runEnd?: string | null; title?: string } = {},
) {
  return makeShowing({
    id,
    category: o.category ?? 'FILM',
    venue: o.venue ?? 'Rio Cinema',
    title: o.title ?? id,
    matchKey: o.matchKey ?? id,
    start: at(start),
    doors: null,
    runtimeMinutes: 90,
    lineup: [],
    genre: null,
    price: null,
    bookingUrl: `https://example.com/${id}`,
    infoUrl: null,
    imageUrl: null,
    tags: [],
    runEnd: o.runEnd ?? null,
  })
}

const now = at('2026-10-25T18:00:00+00:00').ms
const todayDate = listingDateOf(now)

describe('ListingQueries (ported from the app)', () => {
  it('today is chronological and dims started events', () => {
    const result = Q.today(
      [
        showing('late', '2026-10-25T21:00:00+00:00'),
        showing('early', '2026-10-25T14:00:00+00:00'),
        showing('tomorrow', '2026-10-26T19:00:00+00:00'),
      ],
      DEFAULT_FILTERS,
      now,
    )
    expect(result.map((r) => r.showing.id)).toEqual(['early', 'late'])
    expect(result[0].hasStarted).toBe(true)
    expect(result[1].hasStarted).toBe(false)
  })

  it('after midnight counts as tonight', () => {
    const result = Q.today([showing('midnight', '2026-10-26T00:30:00+00:00')], DEFAULT_FILTERS, now)
    expect(result).toHaveLength(1)
    expect(result[0].showing.timeOfDay).toBe('LATE')
  })

  it('filters apply', () => {
    const all = [
      showing('film', '2026-10-25T19:00:00+00:00'),
      showing('gig', '2026-10-25T19:00:00+00:00', { category: 'MUSIC', venue: 'Cafe Oto' }),
      showing('matinee', '2026-10-25T19:00:00+00:00', { venue: 'ICA' }),
    ]
    expect(Q.today(all, makeFilters({ categories: new Set(['MUSIC']) }), now).map((r) => r.showing.id)).toEqual(['gig'])
    expect(
      Q.today(all, makeFilters({ hiddenVenues: new Set(['ICA']) }), now)
        .map((r) => r.showing.id)
        .sort(),
    ).toEqual(['film', 'gig'])
    expect(Q.today(all, makeFilters({ timesOfDay: new Set(['AFTERNOON']) }), now)).toEqual([])
  })

  it('upcoming groups the next fourteen days', () => {
    const result = Q.upcoming(
      [
        showing('today', '2026-10-25T20:00:00+00:00'),
        showing('d1b', '2026-10-26T20:00:00+00:00'),
        showing('d1a', '2026-10-26T19:00:00+00:00'),
        showing('d14', '2026-11-08T19:00:00+00:00'),
        showing('d15', '2026-11-09T19:00:00+00:00'),
      ],
      DEFAULT_FILTERS,
      now,
    )
    expect(result).toHaveLength(2)
    expect(result[0].items.map((i) => i.showing.id)).toEqual(['d1a', 'd1b'])
    expect(result[1].items.map((i) => i.showing.id)).toEqual(['d14'])
  })

  it('film showtimes span venues and skip the past', () => {
    const selected = showing('a', '2026-10-25T20:00:00+00:00', { matchKey: 'nosferatu' })
    const result = Q.showtimes(
      [
        selected,
        showing('b', '2026-10-27T20:00:00+00:00', { venue: 'ICA', matchKey: 'nosferatu' }),
        showing('past', '2026-10-25T12:00:00+00:00', { matchKey: 'nosferatu' }),
        showing('other', '2026-10-26T20:00:00+00:00', { matchKey: 'other film' }),
      ],
      selected,
      now,
    )
    expect(result.flatMap((d) => d.items).map((i) => i.showing.id)).toEqual(['a', 'b'])
  })

  it('the category set allows several', () => {
    const all = [
      showing('film', '2026-10-25T19:00:00+00:00'),
      showing('play', '2026-10-25T19:30:00+00:00', { category: 'THEATRE', venue: 'Park Theatre' }),
      showing('set', '2026-10-25T20:00:00+00:00', { category: 'COMEDY', venue: 'Soho Theatre' }),
    ]
    const f = makeFilters({ categories: new Set(['THEATRE', 'COMEDY']) })
    expect(Q.today(all, f, now).map((r) => r.showing.id)).toEqual(['play', 'set'])
  })

  it('runs are all day, not midnight', () => {
    const run = showing('golden-boy', '2026-09-07T23:00:00+00:00', {
      category: 'THEATRE',
      venue: 'Almeida Theatre',
      runEnd: '2026-10-31',
    })
    const d = Q.day([run], makeFilters({ timesOfDay: new Set(['EVENING']) }), '2026-10-25', now)
    expect(d.items).toEqual([])
    expect(d.runs.map((r) => r.id)).toEqual(['golden-boy'])
    // Not on after its last day.
    expect(Q.day([run], DEFAULT_FILTERS, '2026-11-01', now).runs).toEqual([])
    expect(Q.calendarCounts([run], DEFAULT_FILTERS, now).size).toBe(7) // 25–31 Oct
  })

  it('evening groups one entry per title', () => {
    const groups = Q.evening(
      [
        showing('f1', '2026-10-25T18:10:00+00:00', { venue: 'Curzon Soho', matchKey: 'fatherland' }),
        showing('f2', '2026-10-25T20:30:00+00:00', { venue: 'Curzon Soho', matchKey: 'fatherland' }),
        showing('f3', '2026-10-25T19:00:00+00:00', { venue: 'ICA', matchKey: 'fatherland' }),
        showing('matinee', '2026-10-25T14:00:00+00:00', { venue: 'ICA', matchKey: 'fatherland' }),
        showing('started', '2026-10-25T17:30:00+00:00', { venue: 'Rio Cinema', matchKey: 'naza' }),
        showing('gig', '2026-10-25T19:30:00+00:00', { category: 'MUSIC', venue: 'Cafe Oto' }),
      ],
      DEFAULT_FILTERS,
      now,
    )
    expect(groups.map((g) => g.lead.id)).toEqual(['f1', 'gig', 'started'])
    const fatherland = groups[0]
    expect(fatherland.count).toBe(3)
    expect(fatherland.venues.map((v) => v.venue)).toEqual(['Curzon Soho', 'ICA'])
    expect(fatherland.venues[0].showings.map((s) => s.id)).toEqual(['f1', 'f2'])
    expect(groups[groups.length - 1].allStarted).toBe(true)
  })

  it('morning is its own time of day', () => {
    expect(timeOfDayOf(at('2026-10-25T10:30:00+00:00'))).toBe('MORNING')
    expect(timeOfDayOf(at('2026-10-25T12:00:00+00:00'))).toBe('AFTERNOON')
    expect(timeOfDayOf(at('2026-10-26T01:00:00+00:00'))).toBe('LATE')
  })

  it('by event groups a day', () => {
    const d = Q.day(
      [
        showing('a', '2026-10-25T19:00:00+00:00', { venue: 'ICA', matchKey: 'fatherland' }),
        showing('b', '2026-10-25T21:00:00+00:00', { venue: 'Rio Cinema', matchKey: 'fatherland' }),
        showing('c', '2026-10-25T20:00:00+00:00', { matchKey: 'naza' }),
      ],
      DEFAULT_FILTERS,
      todayDate,
      now,
    )
    const groups = Q.byEvent(d, now)
    expect(groups.map((g) => g.lead.matchKey)).toEqual(['fatherland', 'naza'])
    expect(groups[0].count).toBe(2)
  })

  it('search collates days and ignores filters', () => {
    const t = (k: string) => (k === 'bitter christmas' ? 'Bitter Christmas' : 'A Christmas Carol')
    const mk = (id: string, start: string, venue: string, matchKey: string) =>
      showing(id, start, { venue, matchKey, title: t(matchKey) })
    const all = [
      mk('bc1', '2026-10-28T15:40:00+00:00', 'Curzon Bloomsbury', 'bitter christmas'),
      mk('bc2', '2026-10-29T14:30:00+00:00', 'Curzon Bloomsbury', 'bitter christmas'),
      mk('bc3', '2026-10-29T20:30:00+00:00', 'ICA', 'bitter christmas'),
      mk('past', '2026-10-25T14:30:00+00:00', 'Curzon Bloomsbury', 'bitter christmas'),
      mk('other', '2026-10-28T19:00:00+00:00', 'Rio Cinema', 'christmas carol'),
    ]
    const results = Q.search(all, 'bitter christmas', now)
    expect(results).toHaveLength(1)
    const r = results[0]
    expect(r.days.map((d) => d.date)).toEqual(['2026-10-28', '2026-10-29'])
    expect(r.days[1].venues.map((v) => v.venue)).toEqual(['Curzon Bloomsbury', 'ICA'])
    expect(r.count).toBe(3) // the past showing is excluded
    // Accents, case and venue words all match; title hits rank first.
    expect(Q.search(all, 'CHRISTMAS', now).map((x) => x.title)).toEqual(['Bitter Christmas', 'A Christmas Carol'])
    expect(Q.search(all, 'curzon', now)[0].days).toHaveLength(2)
    expect(normaliseForSearch('Ciné-Lumière')).toBe('cine lumiere')
  })
})

describe('web-only', () => {
  it('rolls the day over at 5am London time, in summer too', () => {
    // 00:30 BST on 2 Jul belongs to 1 Jul; 05:30 BST to 2 Jul.
    expect(listingDateOf(at('2027-07-01T23:30:00+00:00').ms)).toBe('2027-07-01')
    expect(listingDateOf(at('2027-07-02T04:30:00+00:00').ms)).toBe('2027-07-02')
    expect(at('2027-07-01T18:00:00+00:00').hour).toBe(19)
  })

  it('switches BST on and off at 01:00 UTC on the last Sundays of March and October', () => {
    expect(at('2027-03-28T00:59:00+00:00').hour).toBe(0)
    expect(at('2027-03-28T01:00:00+00:00').hour).toBe(2)
    expect(at('2026-10-25T00:59:00+00:00').hour).toBe(1)
    expect(at('2026-10-25T01:00:00+00:00').hour).toBe(1)
    expect(at('2026-10-25T02:00:00+00:00').hour).toBe(2)
  })

  it('counts calendar days from today and skips the past', () => {
    const counts = Q.calendarCounts(
      [
        showing('yesterday', '2026-10-24T19:00:00+00:00'),
        showing('a', '2026-10-25T19:00:00+00:00'),
        showing('b', '2026-10-25T21:00:00+00:00'),
        showing('c', '2026-12-01T19:00:00+00:00'),
      ],
      DEFAULT_FILTERS,
      now,
    )
    expect([...counts]).toEqual([
      ['2026-10-25', 2],
      ['2026-12-01', 1],
    ])
  })

  it('builds the week poster wall: one tile per title, by category, nothing past or beyond the week', () => {
    const wall = Q.week(
      [
        showing('gone', '2026-10-25T14:00:00+00:00', { matchKey: 'gone' }), // started today
        showing('f1', '2026-10-25T20:00:00+00:00', { venue: 'ICA', matchKey: 'fjord' }),
        showing('f2', '2026-10-27T20:00:00+00:00', { venue: 'Rio Cinema', matchKey: 'fjord' }),
        showing('soon', '2026-10-25T19:00:00+00:00', { matchKey: 'naza' }),
        showing('d6', '2026-10-31T19:00:00+00:00', { matchKey: 'last day' }), // today + 6
        showing('d7', '2026-11-01T19:00:00+00:00', { matchKey: 'too late' }), // today + 7
        showing('gig', '2026-10-26T20:00:00+00:00', { category: 'MUSIC', venue: 'Cafe Oto' }),
        showing('play', '2026-09-01T00:00:00+01:00', { category: 'THEATRE', venue: 'Almeida', runEnd: '2026-10-27' }),
      ],
      DEFAULT_FILTERS,
      now,
    )
    expect([...wall.keys()]).toEqual(['FILM', 'MUSIC', 'THEATRE'])
    const films = wall.get('FILM')!
    expect(films.map((t) => t.group.lead.matchKey)).toEqual(['naza', 'fjord', 'last day'])
    expect(films[1].days).toEqual(['2026-10-25', '2026-10-27'])
    expect(wall.get('THEATRE')![0].days).toEqual(['2026-10-25', '2026-10-26', '2026-10-27'])
    // Filters apply.
    expect([...Q.week([showing('gig', '2026-10-26T20:00:00+00:00', { category: 'MUSIC' })], makeFilters({ categories: new Set(['FILM']) }), now).keys()]).toEqual([])
  })

  it('lists venues alphabetically, ignoring "The"', () => {
    const v = Q.venues([
      showing('a', '2026-10-25T19:00:00+00:00', { venue: 'The Nickel' }),
      showing('b', '2026-10-25T19:00:00+00:00', { venue: 'ICA' }),
      showing('c', '2026-10-25T19:00:00+00:00', { venue: 'Rio Cinema', category: 'MUSIC' }),
    ])
    expect(v.map((x) => x.name)).toEqual(['ICA', 'The Nickel', 'Rio Cinema'])
  })
})
