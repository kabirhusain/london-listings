// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

// route.ts reads location/history at import; give it a minimal browser.
vi.stubGlobal('location', { search: '', pathname: '/london-listings/', href: 'https://x/london-listings/' })
vi.stubGlobal('history', { state: null, replaceState: () => {}, pushState: () => {} })
vi.stubGlobal('window', { addEventListener: () => {} })

const { parseRoute, routeSearch } = await import('./route')

describe('URL state', () => {
  it('round-trips every part of a view', () => {
    const search =
      '?tab=upcoming&view=calendar&date=2026-11-28&show=ica%3A1&sel=ica%3A2&cat=film,comedy&hide=ICA%7CRio+Cinema&time=evening,late&arrange=event'
    const r = parseRoute(search)
    expect(r).toMatchObject({ tab: 'upcoming', calendar: true, date: '2026-11-28', show: 'ica:1', sel: 'ica:2', layout: 'BY_EVENT' })
    expect([...r.filters.categories]).toEqual(['FILM', 'COMEDY'])
    expect([...r.filters.hiddenVenues]).toEqual(['ICA', 'Rio Cinema'])
    expect([...r.filters.timesOfDay]).toEqual(['EVENING', 'LATE'])
    expect(parseRoute(routeSearch(r))).toEqual(r)
  })

  it('defaults to Today with no filters, and keeps the bare URL clean', () => {
    const r = parseRoute('')
    expect(r).toMatchObject({ tab: 'today', calendar: false, q: null, show: null, page: null, layout: 'BY_TIME' })
    expect(r.filters.timesOfDay.size).toBe(4)
    expect(routeSearch(r)).toBe('/london-listings/')
  })

  it('handles "no times", an empty search and junk values', () => {
    expect(parseRoute('?time=none').filters.timesOfDay.size).toBe(0)
    expect(routeSearch(parseRoute('?time=none'))).toBe('?time=none')
    expect(parseRoute('?q=').q).toBe('')
    const junk = parseRoute('?tab=nope&date=2026-02-30&cat=opera,film&page=x')
    expect(junk).toMatchObject({ tab: 'today', date: null, page: null })
    expect([...junk.filters.categories]).toEqual(['FILM'])
  })
})
