/** Port of tonight-in-london app/src/test/.../data/ListingsParserTest.kt, plus split-feed cases. */
import { describe, expect, it } from 'vitest'
import { blurbFor } from './models'
import { FeedFormatError, mergeListings, parseListingsText } from './parse'

describe('ListingsParser (ported from the app)', () => {
  it('parses the feed format', () => {
    const listings = parseListingsText(`{
      "generated_at": "2026-10-24T23:44:29+01:00",
      "sources": [{"venue": "a", "status": "ok"}, {"venue": "b", "status": "failed", "error": "x"}],
      "showings": [
        {"id": "pizzaexpress:1", "venue": "PizzaExpress Live Soho", "category": "music",
         "title": "Jazz Dynamos ft. Lucy Randell", "match_key": "jazz dynamos",
         "start": "2026-10-25T13:00:00+00:00", "doors": "2026-10-25T12:00:00+00:00",
         "runtime_minutes": null, "lineup": ["Jazz Dynamos", "Lucy Randell"], "genre": "Jazz",
         "price": "From £28", "booking_url": "https://example.com", "image_url": null,
         "tags": ["sold-out"], "some_future_field": 1},
        {"id": "bad", "venue": "x", "category": "film", "title": "x", "start": "not a date",
         "booking_url": "https://example.com"}
      ]
    }`)
    expect(listings.failedVenues).toEqual(['b'])
    expect(listings.showings).toHaveLength(1)
    const s = listings.showings[0]
    expect(s.category).toBe('MUSIC')
    expect(s.start.hour).toBe(13) // BST ended on 25 Oct 2026, so 13:00Z is 13:00 in London
    expect(s.doors!.hour).toBe(12)
    expect(s.lineup).toEqual(['Jazz Dynamos', 'Lucy Randell'])
    expect(s.imageUrl).toBeNull()
    expect(s.isSoldOut).toBe(true)
    expect(s.sourceSlug).toBe('pizzaexpress')
  })

  it('parses theatre runs and unknown categories', () => {
    const listings = parseListingsText(`{"showings": [
      {"id": "almeida:run:golden-boy", "venue": "Almeida Theatre", "category": "theatre", "kind": "run",
       "title": "Golden Boy", "start": "2026-09-08T00:00:00+01:00", "end": "2026-10-31",
       "booking_url": "https://example.com", "tags": ["run"]},
      {"id": "park:1", "venue": "Park Theatre", "category": "theatre", "kind": "performance",
       "title": "Jumpers", "start": "2026-10-25T19:30:00+00:00", "end": null, "runtime_minutes": 150,
       "booking_url": "https://example.com", "tags": ["venue:Park90"]},
      {"id": "x:1", "venue": "Somewhere", "category": "opera", "title": "Tosca",
       "start": "2026-10-25T19:00:00+00:00", "booking_url": "https://example.com"}
    ]}`)
    const [run, play, opera] = listings.showings
    expect(run.category).toBe('THEATRE')
    expect(run.runEnd).toBe('2026-10-31')
    expect(run.listingDate).toBe('2026-09-08')
    expect(play.runEnd).toBeNull()
    expect(play.runtimeMinutes).toBe(150)
    expect(opera.category).toBe('OTHER')
  })

  it('info_url is optional', () => {
    const listings = parseListingsText(`{"showings": [
      {"id": "a", "venue": "Park Theatre", "category": "theatre", "title": "Jumpers", "start": "2026-10-25T19:30:00+00:00",
       "booking_url": "https://tickets.example/ChooseSeats.aspx?EventInstanceId=1", "info_url": "https://example/whats-on/jumpers"},
      {"id": "b", "venue": "Park Theatre", "category": "theatre", "title": "Jumpers", "start": "2026-10-26T19:30:00+00:00",
       "booking_url": "https://tickets.example/ChooseSeats.aspx?EventInstanceId=2"},
      {"id": "c", "venue": "Park Theatre", "category": "theatre", "title": "Jumpers", "start": "2026-10-26T19:30:00+00:00",
       "booking_url": "https://same.example", "info_url": "https://same.example"}
    ]}`)
    expect(listings.showings[0].infoUrl).toBe('https://example/whats-on/jumpers')
    expect(listings.showings[1].infoUrl).toBeNull()
    expect(listings.showings[2].infoUrl).toBeNull()
  })

  it('looks blurbs up by category and match_key', () => {
    const listings = parseListingsText(`{"blurbs": {"film:2046": "Wong Kar Wai's loose sequel.", "music:2046": "Not this one."},
     "showings": [
      {"id": "a", "venue": "ICA", "category": "film", "title": "2046", "match_key": "2046",
       "start": "2026-10-25T19:30:00+00:00", "booking_url": "https://example.com"},
      {"id": "b", "venue": "ICA", "category": "film", "title": "Other", "match_key": "other",
       "start": "2026-10-25T19:30:00+00:00", "booking_url": "https://example.com"}
    ]}`)
    expect(blurbFor(listings, listings.showings[0])).toBe("Wong Kar Wai's loose sequel.")
    expect(blurbFor(listings, listings.showings[1])).toBeNull()
  })
})

describe('web-only', () => {
  it('rejects files that are not listings', () => {
    expect(() => parseListingsText('<html>')).toThrow(FeedFormatError)
    expect(() => parseListingsText('[1,2]')).toThrow(FeedFormatError)
    expect(() => parseListingsText('{"showings": 3}')).toThrow(FeedFormatError)
  })

  it('reads the credit fields of the split feed', () => {
    const l = parseListingsText(`{"sources": [
      {"venue": "bfi-southbank", "name": "BFI Southbank", "status": "ok",
       "attribution": "Screening data from Clusterflick - clusterflick.com (CC BY 4.0).", "via": "Clusterflick",
       "via_url": "https://clusterflick.com"},
      {"venue": "ica", "status": "stale"}]}`)
    expect(l.sources[0]).toEqual({
      venue: 'bfi-southbank',
      name: 'BFI Southbank',
      status: 'ok',
      attribution: 'Screening data from Clusterflick - clusterflick.com (CC BY 4.0).',
      via: 'Clusterflick',
      viaUrl: 'https://clusterflick.com',
    })
    expect(l.sources[1]).toMatchObject({ name: 'ica', attribution: null, via: null })
  })

  it('merges the two halves of the split feed', () => {
    const show = (id: string, start: string) =>
      `{"id": "${id}", "venue": "V", "category": "film", "title": "${id}", "match_key": "${id}", "start": "${start}", "booking_url": "https://x"}`
    const soon = parseListingsText(`{"generated_at": "2026-11-22T06:00:00+00:00", "blurbs": {"film:a": "A soon."},
      "sources": [{"venue": "v", "status": "stale"}], "showings": [${show('a', '2026-11-22T19:00:00+00:00')}]}`)
    const later = parseListingsText(`{"generated_at": "2026-11-22T06:00:00+00:00", "blurbs": {"film:a": "A later.", "film:b": "B."},
      "sources": [{"venue": "v", "status": "stale"}],
      "showings": [${show('a', '2026-11-22T19:00:00+00:00')}, ${show('b', '2027-01-01T19:00:00+00:00')}]}`)
    const m = mergeListings(soon, later)
    expect(m.showings.map((s) => s.id)).toEqual(['a', 'b'])
    expect(m.blurbs).toEqual({ 'film:a': 'A soon.', 'film:b': 'B.' })
    expect(m.failedVenues).toEqual(['v'])
  })
})
