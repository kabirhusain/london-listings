/**
 * The week as a wall of posters: one tile per title, grouped by category, no times.
 * A web-only view (the app has no equivalent). Clicking a poster opens its detail,
 * which has the showtimes.
 */
import { CATEGORY_LABEL, type Category } from '../../domain/models'
import type { WallTile } from '../../domain/queries'
import * as F from '../../text/format'
import { artSeed, headline, isMusic } from '../../text/showingText'
import { useApp } from '../context'
import { NavLink, Poster } from './basics'
import { SectionHeading } from './rows'

const SECTION: Record<Category, string> = {
  FILM: 'Film',
  MUSIC: 'Music',
  THEATRE: 'Theatre',
  COMEDY: 'Comedy',
  DANCE: 'Dance',
  OTHER: 'Other',
}

function Tile({ tile }: { tile: WallTile }) {
  const { wide, route } = useApp()
  const { group: g } = tile
  const lead = g.lead
  const title = isMusic(lead) ? headline(lead) : g.title
  const venues = g.venues.map((v) => v.venue)
  const selected = wide && (lead.id === route.show || g.venues.some((v) => v.showings.some((s) => s.id === route.show)))
  return (
    <NavLink
      to={{ show: lead.id, sel: null }}
      push={!wide}
      className="wall-tile"
      current={selected ? 'true' : undefined}
      label={`${title}, ${CATEGORY_LABEL[g.category]}, ${venues.length === 1 ? venues[0] : F.count(venues.length, 'venue')}, ${F.count(tile.days.length, 'day')}`}
    >
      <Poster url={tile.image} seed={artSeed(lead)} width="100%" aspect="2 / 3" />
      <span className="wall-caption">{title}</span>
    </NavLink>
  )
}

export function PosterWall({ wall }: { wall: Map<Category, WallTile[]> }) {
  return (
    <div className="wall">
      {[...wall].map(([category, tiles]) => (
        <section key={category} className="wall-section" aria-label={SECTION[category]}>
          <SectionHeading title={SECTION[category]} note={F.count(tiles.length, 'title')} />
          <div className="wall-grid">
            {tiles.map((t) => (
              <Tile key={t.group.key} tile={t} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
