/** Port of FilterSheet.kt. On phones it's a bottom sheet; on wide screens it sits in the left rail. Filters apply live. */
import { useEffect, useRef } from 'react'
import { DEFAULT_FILTERS, includesCategory, isDefault, type Filters } from '../../domain/filters'
import { CATEGORIES, CATEGORY_LABEL, TIME_OF_DAY_LABEL, TIMES_OF_DAY, type Category } from '../../domain/models'
import { venues as venuesOf, type Venue } from '../../domain/queries'
import { navigate } from '../../data/route'
import * as F from '../../text/format'
import { useApp } from '../context'
import { ArrowIcon, CloseIcon } from './basics'

function toggle<T>(set: ReadonlySet<T>, x: T): Set<T> {
  const s = new Set(set)
  if (s.has(x)) s.delete(x)
  else s.add(x)
  return s
}

function FilterControls() {
  const { route, listings } = useApp()
  const f = route.filters
  const set = (patch: Partial<Filters>) => navigate({ filters: { ...f, ...patch } })
  const all = venuesOf(listings?.showings ?? [])
  const present = CATEGORIES.filter((c) => all.some((v) => v.categories.has(c)))
  const relevant = all.filter((v) => [...v.categories].some((c) => includesCategory(f, c)))
  const groups: [string, Venue[]][] = [
    ['Cinemas', relevant.filter((v) => v.categories.has('FILM'))],
    ['Music', relevant.filter((v) => !v.categories.has('FILM') && v.categories.has('MUSIC'))],
    ['Theatre & stage', relevant.filter((v) => !v.categories.has('FILM') && !v.categories.has('MUSIC'))],
  ]

  return (
    <>
      {route.tab !== 'evening' && (
        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend className="t-legend muted filter-legend" style={{ float: 'left', width: '100%' }}>
            Arrange
          </legend>
          <div className="tiles two" style={{ clear: 'both' }}>
            {(
              [
                ['BY_TIME', 'By time', 'Every performance'],
                ['BY_EVENT', 'By event', 'One entry per title'],
              ] as const
            ).map(([layout, label, detail]) => (
              <button key={layout} className="tile has-detail" aria-pressed={route.layout === layout} onClick={() => navigate({ layout })}>
                <span className="t-toggle">{label}</span>
                <span className="t-meta">{detail}</span>
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
        <legend className="t-legend muted filter-legend" style={{ float: 'left', width: '100%' }}>
          Show
        </legend>
        <div className="tiles" style={{ clear: 'both' }}>
          <button className="tile" aria-pressed={f.categories.size === 0} onClick={() => set({ categories: new Set() })}>
            <span className="t-toggle">All</span>
          </button>
          {present.map((c: Category) => (
            <button key={c} className="tile" aria-pressed={f.categories.has(c)} onClick={() => set({ categories: toggle(f.categories, c) })}>
              <span className="t-toggle">{CATEGORY_LABEL[c]}</span>
            </button>
          ))}
        </div>
      </fieldset>

      {groups
        .filter(([, vs]) => vs.length > 0)
        .map(([name, vs]) => (
          <fieldset key={name} style={{ border: 0, margin: 0, padding: 0 }}>
            <div className="legend-row filter-legend tight">
              <legend className="t-legend muted" style={{ float: 'left' }}>
                {name}
              </legend>
              <span>
                <button
                  className="text-link t-monoLabel"
                  onClick={() => {
                    const hidden = new Set(f.hiddenVenues)
                    vs.forEach((v) => hidden.delete(v.name))
                    set({ hiddenVenues: hidden })
                  }}
                >
                  All
                </button>
                <button
                  className="text-link t-monoLabel"
                  onClick={() => set({ hiddenVenues: new Set([...f.hiddenVenues, ...vs.map((v) => v.name)]) })}
                >
                  None
                </button>
              </span>
            </div>
            {vs.map((v) => (
              <button
                key={v.name}
                className="switch-row"
                role="switch"
                aria-checked={!f.hiddenVenues.has(v.name)}
                onClick={() => set({ hiddenVenues: toggle(f.hiddenVenues, v.name) })}
              >
                <span className="t-listTitle">{v.name}</span>
                <span className="switch" aria-hidden="true" />
              </button>
            ))}
          </fieldset>
        ))}

      <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
        <legend className="t-legend muted filter-legend time" style={{ float: 'left', width: '100%' }}>
          Time of day
        </legend>
        <div className="tiles two" style={{ clear: 'both' }}>
          {TIMES_OF_DAY.map((t) => (
            <button key={t} className="tile has-detail" aria-pressed={f.timesOfDay.has(t)} onClick={() => set({ timesOfDay: toggle(f.timesOfDay, t) })}>
              <span className="t-toggle">{TIME_OF_DAY_LABEL[t]}</span>
              <span className="t-meta">{F.TIME_RANGE[t]}</span>
            </button>
          ))}
        </div>
      </fieldset>
    </>
  )
}

function ResetButton() {
  const { route } = useApp()
  return (
    <button className="text-link t-monoLabel" disabled={isDefault(route.filters)} onClick={() => navigate({ filters: DEFAULT_FILTERS })}>
      Reset
    </button>
  )
}

/** Phone: modal bottom sheet. */
export function FilterSheet({ count, onClose }: { count: number; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      prev?.focus()
    }
  }, [onClose])
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Filter" ref={ref} tabIndex={-1}>
        <div className="sheet-handle" />
        <div className="sheet-head">
          <h2 className="t-dayHeader" style={{ margin: 0 }}>
            Filter
          </h2>
          <ResetButton />
          <button className="icon-btn bare" onClick={onClose} aria-label="Close filters">
            <CloseIcon />
          </button>
        </div>
        <div className="sheet-body">
          <FilterControls />
        </div>
        <div className="sheet-foot">
          <button className="btn-accent t-buttonLarge" onClick={onClose}>
            Show {F.count(count, 'showing')}
            <ArrowIcon />
          </button>
        </div>
      </div>
    </>
  )
}

/** Wide screens: the same controls, always visible in the left rail. */
export function FilterRail() {
  return (
    <section className="filters-inline-wrap" aria-label="Filters">
      <div className="sheet-head">
        <h2 className="t-dayHeader" style={{ margin: 0 }}>
          Filter
        </h2>
        <ResetButton />
      </div>
      <div className="filters-inline">
        <FilterControls />
      </div>
    </section>
  )
}
