/** Ports of States.kt and ListingsList.kt's empty states, plus the footer with the data credits. */
import type { ReactNode } from 'react'
import {
  categoriesDefault,
  DEFAULT_FILTERS,
  includesCategory,
  isDefault,
  timesDefault,
  venuesDefault,
  type Filters,
} from '../../domain/filters'
import { CATEGORIES, CATEGORY_LABEL, TIME_OF_DAY_LABEL, TIMES_OF_DAY } from '../../domain/models'
import { venues } from '../../domain/queries'
import { navigate } from '../../data/route'
import { dismissRefreshError, load } from '../../data/feed'
import * as F from '../../text/format'
import { useApp } from '../context'
import { Attribution, CloseIcon, NavLink } from './basics'

export function MessageState({
  title,
  body,
  primary,
  secondary,
}: {
  title: string
  body: ReactNode
  primary?: { label: string; onClick: () => void }
  secondary?: { label: string; onClick: () => void }
}) {
  return (
    <div className="message" role="status">
      <h2 className="t-emptyTitle" style={{ margin: 0, whiteSpace: 'pre-line' }}>
        {title}
      </h2>
      <p className="t-monoBody muted">{body}</p>
      {(primary || secondary) && (
        <div className="actions">
          {primary && (
            <button className="btn-accent t-button" onClick={primary.onClick}>
              {primary.label}
            </button>
          )}
          {secondary && (
            <button className="btn-outline t-button" onClick={secondary.onClick}>
              {secondary.label}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const BAR_WIDTHS = [
  [0.78, 0.52, 0.64],
  [0.46, 0.6, 0.58],
  [0.88, 0.44, 0.7],
  [0.62, 0.56, 0.6],
  [0.7, 0.4, 0.66],
  [0.54, 0.58, 0.62],
  [0.82, 0.48, 0.68],
]

export function LoadingState() {
  return (
    <div aria-busy="true" aria-label="Loading listings">
      {BAR_WIDTHS.map((w, i) => (
        <div className="skel-row" key={i} style={{ animationDelay: `${i * 0.12}s` }}>
          <div className="b" style={{ width: 46, height: 16 }} />
          <div className="bars">
            <div className="b" style={{ height: 20, width: `${w[0] * 100}%` }} />
            <div className="b" style={{ height: 13, width: `${w[1] * 100}%` }} />
            <div className="b" style={{ height: 10, width: `${w[2] * 100}%` }} />
          </div>
          <div className="b" style={{ width: 48, height: 72 }} />
        </div>
      ))}
    </div>
  )
}

export function NoSignal() {
  const { feed } = useApp()
  return (
    <MessageState
      title="No signal."
      body={`${F.error(feed.error ?? 'OFFLINE')} Listings are saved after the first download, so this only happens until one succeeds.`}
      primary={{ label: 'Retry', onClick: () => void load(true) }}
    />
  )
}

/** The labels of the filter chips shown above an empty list (ListingsList.kt filterChips). */
export function filterChips(f: Filters, allVenues: ReturnType<typeof venues>): { label: string; clear: Partial<Filters> }[] {
  const chips: { label: string; clear: Partial<Filters> }[] = []
  if (!categoriesDefault(f)) {
    const labels = CATEGORIES.filter((c) => f.categories.has(c)).map((c) => CATEGORY_LABEL[c])
    chips.push({ label: `${labels.join(' + ')} only`, clear: { categories: new Set() } })
  }
  if (!venuesDefault(f)) {
    const relevant = allVenues.filter((v) => [...v.categories].some((c) => includesCategory(f, c)))
    const shown = relevant.filter((v) => !f.hiddenVenues.has(v.name))
    const label =
      shown.length === 0 ? 'No venues' : shown.length === 1 ? `${shown[0].name} only` : `${F.count(f.hiddenVenues.size, 'venue')} off`
    chips.push({ label, clear: { hiddenVenues: new Set() } })
  }
  if (!timesDefault(f)) {
    const label =
      f.timesOfDay.size === 0
        ? 'No times'
        : TIMES_OF_DAY.filter((t) => f.timesOfDay.has(t))
            .map((t) => `${TIME_OF_DAY_LABEL[t]} ${F.TIME_RANGE[t]}`)
            .join(' + ')
    chips.push({ label, clear: { timesOfDay: DEFAULT_FILTERS.timesOfDay } })
  }
  return chips
}

/** Number of filter groups that differ from the default, for the "Filters · N" badge. */
export function activeFilterGroups(f: Filters): number {
  return [!categoriesDefault(f), !venuesDefault(f), !timesDefault(f)].filter(Boolean).length
}

export function FilteredEmpty({ filteredBody, unfilteredBody, onEdit }: { filteredBody: string; unfilteredBody: string; onEdit: () => void }) {
  const { route, listings } = useApp()
  const f = route.filters
  if (isDefault(f)) return <MessageState title={'Nothing\non.'} body={unfilteredBody} />
  const chips = filterChips(f, venues(listings?.showings ?? []))
  return (
    <>
      <div className="chips">
        <span className="t-tag muted" style={{ fontSize: 11 }}>
          Showing
        </span>
        {chips.map((c) => (
          <button key={c.label} className="chip t-monoLabel" onClick={() => navigate({ filters: { ...f, ...c.clear } })} aria-label={`Remove filter: ${c.label}`}>
            {c.label}
            <CloseIcon size={14} stroke={2.4} />
          </button>
        ))}
      </div>
      <MessageState
        title={'Nothing\non.'}
        body={filteredBody}
        primary={{ label: 'Clear filters', onClick: () => navigate({ filters: DEFAULT_FILTERS }) }}
        secondary={{ label: 'Edit', onClick: onEdit }}
      />
    </>
  )
}

/** The distinct licence credits the current listings carry (e.g. Clusterflick, CC BY 4.0). */
export function useAttributions(): string[] {
  const { listings } = useApp()
  return [...new Set((listings?.sources ?? []).map((s) => s.attribution).filter((a): a is string => !!a))]
}

/** Bottom of every list: how fresh the data is, and the credits the data's licences require. */
export function Freshness() {
  const { listings, now } = useApp()
  const attributions = useAttributions()
  if (!listings) return null
  const failed = listings.failedVenues.length
  return (
    <footer className="freshness">
      <span className="t-tag muted">
        {F.updated(listings.generatedAt?.ms ?? null, now)}
        {failed > 0 && ` · ${F.count(failed, 'venue')} couldn't be updated`}
      </span>
      {attributions.map((a) => (
        <span key={a} className="credit">
          <Attribution text={a} />
        </span>
      ))}
      <span className="credit">
        Listings, descriptions and images belong to the venues and the services credited.{' '}
        <NavLink to={{ page: 'credits', show: null, q: null }} push>
          Credits and sources
        </NavLink>{' '}
        · <a href="status.html">Venue status</a>
      </span>
    </footer>
  )
}

export function Snackbar() {
  const { feed } = useApp()
  if (!feed.refreshFailed || !feed.error) return null
  return (
    <div className="snackbar t-meta" role="alert">
      <span>Couldn't refresh. {F.error(feed.error)} Showing saved listings.</span>
      <button
        className="t-monoLabel"
        onClick={() => {
          dismissRefreshError()
          void load(true)
        }}
      >
        Retry
      </button>
    </div>
  )
}
