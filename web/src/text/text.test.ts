import { describe, expect, it } from 'vitest'
import { makeShowing } from '../domain/models'
import { parseInstant } from '../domain/time'
import * as F from './format'
import { javaHashCode, posterArt } from './posterArt'
import { compactSub, headline, rowMeta, runLabel, screen, timing } from './showingText'

const at = (s: string) => parseInstant(s)!
const base = {
  id: 'ica:1',
  category: 'FILM' as const,
  venue: 'ICA',
  title: 'Paris, Texas',
  matchKey: 'paris texas',
  start: at('2026-11-22T19:30:00+00:00'),
  doors: null,
  runtimeMinutes: 145,
  lineup: [],
  genre: null,
  price: null,
  bookingUrl: 'https://x',
  infoUrl: null,
  imageUrl: null,
  tags: ['screen:2'],
  runEnd: null,
}

describe('Format', () => {
  it('formats dates like java.time in Locale.UK', () => {
    expect(F.longDay('2026-11-22')).toBe('Sunday 22 November')
    expect(F.shortDay('2026-09-01')).toBe('Tue 1 Sep')
    expect(F.numericDate('2026-11-02')).toBe('02.11.26')
    expect(F.dateRange('2026-11-23', '2026-12-06')).toBe('23.11 – 06.12')
    expect(F.relativeDay('2026-11-22', '2026-11-22')).toBe('Today')
    expect(F.relativeDay('2026-11-23', '2026-11-22')).toBe('Tomorrow')
    expect(F.relativeDay('2026-11-24', '2026-11-22')).toBe('Tue 24 Nov')
    expect(F.monthYear('2026-11-22')).toBe('November 2026')
    expect(F.count(1, 'showing')).toBe('1 showing')
    expect(F.count(2, 'venue')).toBe('2 venues')
  })

  it('says how fresh the listings are', () => {
    const t = at('2026-11-22T06:04:00+00:00').ms
    expect(F.updated(null, t)).toBe('Not updated yet')
    expect(F.updated(t, t + 30_000)).toBe('Updated just now')
    expect(F.updated(t, t + 5 * 60_000)).toBe('Updated 5 min ago')
    expect(F.updated(t, t + 5 * 3_600_000)).toBe('Updated at 06:04')
    expect(F.updated(t, t + 30 * 3_600_000)).toBe('Updated Sun 22 Nov')
  })
})

describe('ShowingText', () => {
  it('builds the row meta for films, gigs and runs', () => {
    expect(rowMeta(makeShowing(base))).toBe('Screen 2 · 145 min · ends 21:55')
    const gig = makeShowing({
      ...base,
      category: 'MUSIC',
      lineup: ['Headliner', 'Support A', 'Support B'],
      doors: at('2026-11-22T19:00:00+00:00'),
      price: 'From £16',
      tags: ['sold-out'],
    })
    expect(headline(gig)).toBe('Headliner')
    expect(rowMeta(gig)).toBe('with Support A, Support B · Doors 19:00 · From £16 · Sold out')
    expect(compactSub(gig)).toBe('ICA · Doors 19:00 · From £16 · Sold out')
    expect(rowMeta(makeShowing({ ...base, category: 'MUSIC', tags: [] }))).toBe('Live music')
    const run = makeShowing({ ...base, category: 'THEATRE', tags: ['run'], runEnd: '2026-12-23' })
    expect(rowMeta(run)).toBe('Performance times not listed')
    expect(runLabel(run, '2026-11-22')).toBe('Until Wed 23 Dec')
    expect(runLabel(run, '2026-12-23')).toBe('Last day today')
    expect(compactSub(run)).toBe('ICA · Theatre · 145 min')
  })

  it('reads screens and timing', () => {
    expect(screen(makeShowing({ ...base, tags: ['venue:Park90'] }))).toBe('Park90')
    expect(screen(makeShowing({ ...base, tags: [] }))).toBeNull()
    const s = makeShowing(base)
    expect(timing(s, s.start.ms - 1)).toBe('UPCOMING')
    expect(timing(s, s.start.ms + 60_000)).toBe('STARTED')
    expect(timing(s, s.start.ms + 145 * 60_000)).toBe('ENDED')
    expect(timing(makeShowing({ ...base, runtimeMinutes: null }), s.start.ms + 9e9)).toBe('STARTED')
  })
})

describe('poster art', () => {
  it("matches Java's String.hashCode", () => {
    // "hello" == 99162322 is the well-known JVM value; the others were computed with an
    // independent big-integer implementation of the definition over UTF-16 code units.
    expect(javaHashCode('')).toBe(0)
    expect(javaHashCode('a')).toBe(97)
    expect(javaHashCode('hello')).toBe(99162322)
    expect(javaHashCode('paris texas')).toBe(1448146884)
    expect(javaHashCode('the quick brown fox jumps over')).toBe(768645004)
    expect(javaHashCode('Ciné 🎬')).toBe(-1845369297)
  })

  it('picks colours and a shape from the seed', () => {
    const h = Math.abs(javaHashCode('paris texas'))
    expect(posterArt('paris texas').shape).toBe(['SUN', 'BAND', 'STRIPE', 'DOT', 'RING', 'SPLIT', 'FRAME'][Math.floor(h / 17) % 7])
    expect(posterArt('paris texas')).toEqual(posterArt('paris texas'))
  })
})
