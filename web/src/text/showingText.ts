/** Port of tonight-in-london ui/ShowingText.kt: presentation helpers derived only from feed fields. */
import { CATEGORY_LABEL, type Showing } from '../domain/models'
import { londonTime, MINUTE, type LondonTime } from '../domain/time'
import { relativeDay, time } from './format'

export const isMusic = (s: Showing) => s.category === 'MUSIC'

/** Seed for generated poster art: same film → same art at every venue. */
export const artSeed = (s: Showing) => (isMusic(s) ? s.id : s.matchKey)

/** Gigs lead with the headliner; films with the title. */
export const headline = (s: Showing) => (isMusic(s) ? (s.lineup[0] ?? s.title) : s.title)

export const supportActs = (s: Showing) => (isMusic(s) ? s.lineup.slice(1) : [])

/**
 * "Screen 1", "NFT2", "Lilian Baylis Studio": the room within the venue, from a `screen:` tag
 * (cinemas) or `venue:` tag (theatres), if the venue provides one.
 */
export function screen(s: Showing): string | null {
  const tag = s.tags.find((t) => t.startsWith('screen:') || t.startsWith('venue:'))
  if (!tag) return null
  const v = tag.slice(tag.indexOf(':') + 1).trim()
  if (!v) return null
  return /^\d+$/.test(v) ? `Screen ${v}` : v
}

/** "Until Sat 31 Oct" for a run; null for a dated performance. */
export function runLabel(s: Showing, today: string): string | null {
  if (s.runEnd === null) return null
  return s.runEnd === today ? 'Last day today' : `Until ${relativeDay(s.runEnd, today)}`
}

/** End time, only when we know the runtime. */
export function endTime(s: Showing): LondonTime | null {
  return s.runtimeMinutes !== null ? londonTime(s.start.ms + s.runtimeMinutes * MINUTE) : null
}

export type Timing = 'UPCOMING' | 'STARTED' | 'ENDED'

export function timing(s: Showing, now: number): Timing {
  if (s.start.ms > now) return 'UPCOMING'
  const end = endTime(s)
  return end !== null && end.ms <= now ? 'ENDED' : 'STARTED'
}

const join = (items: (string | null | undefined | false)[]) => items.filter(Boolean).join(' · ')

/** Mono metadata line in a Today row. */
export function rowMeta(s: Showing): string {
  if (s.isRun) return join(['Performance times not listed', s.isSoldOut && 'Sold out'])
  if (isMusic(s)) {
    const acts = supportActs(s)
    return (
      join([
        acts.length > 0 && `with ${acts.join(', ')}`,
        s.doors && `Doors ${time(s.doors)}`,
        s.price,
        s.isSoldOut && 'Sold out',
      ]) || 'Live music'
    )
  }
  const end = endTime(s)
  return join([
    screen(s),
    s.runtimeMinutes !== null && `${s.runtimeMinutes} min`,
    end && `ends ${time(end)}`,
    s.isSoldOut && 'Sold out',
  ])
}

/** Second line in an Upcoming row. */
export function compactSub(s: Showing): string {
  return join([
    s.venue,
    s.category !== 'FILM' && s.category !== 'MUSIC' && CATEGORY_LABEL[s.category],
    isMusic(s)
      ? s.doors
        ? `Doors ${time(s.doors)}`
        : 'Live music'
      : s.runtimeMinutes !== null && `${s.runtimeMinutes} min`,
    isMusic(s) && s.price,
    s.isSoldOut && 'Sold out',
  ])
}
