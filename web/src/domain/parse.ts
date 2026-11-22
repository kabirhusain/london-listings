/**
 * Port of tonight-in-london data/remote/ListingsParser.kt. Reads listings.json, or either
 * half of the website's split feed (data/soon.json, data/later.json), which share its shape.
 * Unknown fields are ignored so the feed can grow safely; one malformed entry is dropped
 * rather than taking the whole feed down.
 */
import { categoryOf, makeShowing, type Listings, type Showing, type Source } from './models'
import { parseDate, parseInstant } from './time'

export class FeedFormatError extends Error {}

type Json = Record<string, unknown>
const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v)
const str = (v: unknown): string | null => (typeof v === 'string' ? v : null)
const nonBlank = (v: unknown): string | null => {
  const s = str(v)
  return s !== null && s.trim() !== '' ? s : null
}
const strList = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : [])

function showingOf(d: unknown): Showing | null {
  if (!isObj(d)) return null
  const id = str(d.id)
  const venue = str(d.venue)
  const title = str(d.title)
  const bookingUrl = str(d.booking_url)
  const category = str(d.category)
  const start = typeof d.start === 'string' ? parseInstant(d.start) : null
  if (!id || venue === null || title === null || bookingUrl === null || category === null || !start) return null
  // A run without a parsable last day is treated as on for its first day only.
  let runEnd: string | null = null
  if (str(d.kind)?.toLowerCase() === 'run') {
    const endText = str(d.end)
    const end = endText ? (parseInstant(endText)?.date ?? parseDate(endText)) : null
    runEnd = end && end >= start.date ? end : start.date
  }
  const runtime = typeof d.runtime_minutes === 'number' && d.runtime_minutes > 0 ? Math.trunc(d.runtime_minutes) : null
  const infoUrl = str(d.info_url)
  const matchKey = nonBlank(d.match_key)
  return makeShowing({
    id,
    category: categoryOf(category),
    venue,
    title,
    matchKey: matchKey ?? title.toLowerCase().trim(),
    start,
    doors: typeof d.doors === 'string' ? parseInstant(d.doors) : null,
    runtimeMinutes: runtime,
    lineup: strList(d.lineup).filter((x) => x.trim() !== ''),
    genre: nonBlank(d.genre),
    price: nonBlank(d.price),
    bookingUrl,
    infoUrl: infoUrl && infoUrl.startsWith('http') && infoUrl !== bookingUrl ? infoUrl : null,
    imageUrl: nonBlank(d.image_url),
    tags: strList(d.tags),
    runEnd,
  })
}

function sourceOf(d: unknown): Source | null {
  if (!isObj(d) || typeof d.venue !== 'string') return null
  return {
    venue: d.venue,
    name: str(d.name) ?? d.venue,
    status: str(d.status),
    attribution: nonBlank(d.attribution),
    via: nonBlank(d.via),
    viaUrl: nonBlank(d.via_url),
  }
}

/** Throws FeedFormatError if the document isn't in the expected shape. */
export function parseListings(doc: unknown): Listings {
  if (!isObj(doc)) throw new FeedFormatError('The listings file is not a JSON object.')
  if (doc.showings !== undefined && !Array.isArray(doc.showings)) throw new FeedFormatError('"showings" is not a list.')
  const sources = (Array.isArray(doc.sources) ? doc.sources : []).map(sourceOf).filter((s): s is Source => s !== null)
  const blurbs: Record<string, string> = {}
  if (isObj(doc.blurbs)) {
    for (const [k, v] of Object.entries(doc.blurbs)) {
      if (typeof v === 'string' && v.trim() !== '') blurbs[k] = v.trim()
    }
  }
  return {
    generatedAt: typeof doc.generated_at === 'string' ? parseInstant(doc.generated_at) : null,
    showings: ((doc.showings as unknown[] | undefined) ?? []).map(showingOf).filter((s): s is Showing => s !== null),
    failedVenues: sources.filter((s) => s.status !== null && s.status !== 'ok').map((s) => s.venue),
    blurbs,
    sources,
  }
}

export function parseListingsText(text: string): Listings {
  let doc: unknown
  try {
    doc = JSON.parse(text)
  } catch {
    throw new FeedFormatError('The listings file is not valid JSON.')
  }
  return parseListings(doc)
}

/** Combines the two halves of the split feed. Showings are unique by id; the first half wins. */
export function mergeListings(a: Listings, b: Listings): Listings {
  const ids = new Set(a.showings.map((s) => s.id))
  return {
    generatedAt: a.generatedAt ?? b.generatedAt,
    showings: [...a.showings, ...b.showings.filter((s) => !ids.has(s.id))],
    failedVenues: a.failedVenues,
    blurbs: { ...b.blurbs, ...a.blurbs },
    sources: a.sources.length ? a.sources : b.sources,
  }
}
