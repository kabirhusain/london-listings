/** Port of tonight-in-london domain/Models.kt. Pure: no DOM, no React. */
import { DAY_ROLLOVER_HOUR, listingDateOf, type LondonTime } from './time'

export const CATEGORIES = ['FILM', 'MUSIC', 'THEATRE', 'COMEDY', 'DANCE', 'OTHER'] as const
export type Category = (typeof CATEGORIES)[number]

export const CATEGORY_LABEL: Record<Category, string> = {
  FILM: 'Film',
  MUSIC: 'Music',
  THEATRE: 'Theatre',
  COMEDY: 'Comedy',
  DANCE: 'Dance',
  OTHER: 'Other',
}

/** A category the app doesn't know yet becomes OTHER, so new feed categories still show. */
export function categoryOf(raw: string): Category {
  const up = raw.toUpperCase()
  return (CATEGORIES as readonly string[]).includes(up) ? (up as Category) : 'OTHER'
}

export const TIMES_OF_DAY = ['MORNING', 'AFTERNOON', 'EVENING', 'LATE'] as const
export type TimeOfDay = (typeof TIMES_OF_DAY)[number]

export const TIME_OF_DAY_LABEL: Record<TimeOfDay, string> = {
  MORNING: 'Morning',
  AFTERNOON: 'Afternoon',
  EVENING: 'Evening',
  LATE: 'Late',
}

export function timeOfDayOf(t: LondonTime): TimeOfDay {
  const h = t.hour
  if (h < DAY_ROLLOVER_HOUR) return 'LATE'
  if (h < 12) return 'MORNING'
  if (h < 17) return 'AFTERNOON'
  if (h < 22) return 'EVENING'
  return 'LATE'
}

/** Lower-case, accents stripped, punctuation to spaces: "Ciné-Lumière" → "cine lumiere". */
export function normaliseForSearch(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Mn}+/gu, '')
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
}

export interface Showing {
  id: string
  category: Category
  venue: string
  title: string
  /** Normalised title used to find the same film at other venues. */
  matchKey: string
  start: LondonTime
  doors: LondonTime | null
  runtimeMinutes: number | null
  /** Headliner first. */
  lineup: string[]
  genre: string | null
  price: string | null
  bookingUrl: string
  /** The venue's information page, when the feed provides one separately from bookingUrl. */
  infoUrl: string | null
  imageUrl: string | null
  tags: string[]
  /**
   * Last day of a run ("YYYY-MM-DD") for entries the feed lists as a whole run (kind "run").
   * Runs have no real start time: start is midnight on the first day.
   */
  runEnd: string | null
  // Derived once at parse time:
  isRun: boolean
  listingDate: string
  timeOfDay: TimeOfDay
  /** Title, venue, category and performers, normalised for search. */
  searchText: string
  isSoldOut: boolean
  certificate: string | null
  /** Tags worth showing to a person (format/access flags), without the internal key:value ones. */
  displayTags: string[]
  /** The collector's venue slug, from the id ("<slug>:..."); links a showing to its source's credits. */
  sourceSlug: string
}

export type ShowingInput = Omit<
  Showing,
  'isRun' | 'listingDate' | 'timeOfDay' | 'searchText' | 'isSoldOut' | 'certificate' | 'displayTags' | 'sourceSlug'
>

export function makeShowing(s: ShowingInput): Showing {
  const isRun = s.runEnd !== null
  return {
    ...s,
    isRun,
    listingDate: isRun ? s.start.date : listingDateOf(s.start.ms),
    timeOfDay: timeOfDayOf(s.start),
    searchText: normaliseForSearch([s.title, s.venue, CATEGORY_LABEL[s.category], s.lineup.join(' ')].join(' ')),
    isSoldOut: s.tags.includes('sold-out'),
    certificate: s.tags.find((t) => t.startsWith('cert:'))?.slice(5) ?? null,
    displayTags: s.tags.filter((t) => !t.includes(':') && t !== 'movie' && t !== 'sold-out' && t !== 'run'),
    sourceSlug: s.id.includes(':') ? s.id.slice(0, s.id.indexOf(':')) : '',
  }
}

/** True if this is a run that's on during [date]. */
export function runsOn(s: Showing, date: string): boolean {
  return s.runEnd !== null && date >= s.listingDate && date <= s.runEnd
}

/** One source (venue) in the feed, with what the site needs to credit it. */
export interface Source {
  venue: string
  name: string
  status: string | null
  /** Licence credit that must be shown wherever this source's data is (e.g. Clusterflick, CC BY 4.0). */
  attribution: string | null
  /** Aggregator the listings come from ("Clusterflick", "Songkick", "DICE"), and where to link. */
  via: string | null
  viaUrl: string | null
}

export interface Listings {
  generatedAt: LondonTime | null
  showings: Showing[]
  /** Venues whose data couldn't be refreshed upstream; their listings may be stale or missing. */
  failedVenues: string[]
  /** Short description per title, keyed "<category>:<match_key>" as in the feed. */
  blurbs: Record<string, string>
  sources: Source[]
}

/** The title's description, shared by every performance of it at any venue. */
export function blurbFor(listings: Listings, s: Showing): string | null {
  return listings.blurbs[`${s.category.toLowerCase()}:${s.matchKey}`] ?? null
}
