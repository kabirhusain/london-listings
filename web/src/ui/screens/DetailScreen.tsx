/** Port of DetailScreen.kt: film/stage layout, gig layout and the booking bar; plus the event's source credit. */
import { useMemo, type ReactNode } from 'react'
import { blurbFor, CATEGORY_LABEL, type Showing } from '../../domain/models'
import * as Q from '../../domain/queries'
import { goBack, navigate } from '../../data/route'
import * as F from '../../text/format'
import { artSeed, isMusic, runLabel, screen } from '../../text/showingText'
import { useApp } from '../context'
import { ArrowUpRightIcon, Attribution, BackArrowIcon, CloseIcon, ExtLink, FitText, Poster } from '../components/basics'
import { SectionHeading } from '../components/rows'
import { LoadingState, MessageState } from '../components/states'

function BackBar() {
  const { wide, backLabel } = useApp()
  const close = () => goBack({ show: null, sel: null })
  return (
    <div className="backbar">
      <button onClick={close} aria-label={wide ? 'Close details' : `Back to ${backLabel}`}>
        {wide ? <CloseIcon size={18} /> : <BackArrowIcon />}
        {wide ? 'Close' : backLabel}
      </button>
    </div>
  )
}

function DataItem({ term, value, now = false }: { term: string; value: ReactNode | null | undefined; now?: boolean }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className={now ? 'now' : undefined}>
      <dt className="t-dataTerm muted">{term}</dt>
      <dd className="t-dataValue">{value}</dd>
    </div>
  )
}

/** Gig items always show; a missing value says so. */
function GigItem({ term, value, now = false }: { term: string; value: string | null; now?: boolean }) {
  return (
    <div className={value && now ? 'now' : undefined}>
      <dt className="t-dataTerm muted">{term}</dt>
      <dd className={`t-dataValue ${value ? '' : 'muted'}`}>{value ?? 'Not listed'}</dd>
    </div>
  )
}

function Blurb({ text }: { text: string | null }) {
  if (!text) return null
  return (
    <div className="blurb">
      <p className="t-blurb">{text}</p>
    </div>
  )
}

/** Where this listing came from, with any licence credit it carries. Shown on every event. */
function SourceLine({ s }: { s: Showing }) {
  const { sources } = useApp()
  const src = sources.get(s.sourceSlug)
  // Clusterflick only supplies films (e.g. Rich Mix's gigs come from elsewhere).
  const credited = src?.via !== 'Clusterflick' || s.category === 'FILM'
  return (
    <div className="source-line credit">
      <span>
        Listing and image from {s.venue}
        {src?.via && credited && (
          <>
            {' '}
            via {src.viaUrl ? <ExtLink href={src.viaUrl}>{src.via}</ExtLink> : src.via}
          </>
        )}
        . Times can change: check with the venue before you go.
      </span>
      {src?.attribution && credited && (
        <span>
          <Attribution text={src.attribution} />
        </span>
      )}
    </div>
  )
}

function BookBar({ s, sub }: { s: Showing; sub: string }) {
  const label = s.infoUrl ? 'Info & tickets' : s.isSoldOut ? 'Sold out · View' : 'Book'
  return (
    <div className={`bookbar ${s.infoUrl ? 'with-link' : ''}`}>
      <a className="book" href={s.infoUrl ?? s.bookingUrl} target="_blank" rel="noopener noreferrer">
        <span>
          <span className="t-bookLabel">{label}</span>
          <span className="sub">{sub}</span>
        </span>
        <ArrowUpRightIcon />
      </a>
      {s.infoUrl && (
        <a className="text-link t-monoLabel checkout-link" href={s.bookingUrl} target="_blank" rel="noopener noreferrer">
          {s.isSoldOut ? 'Sold out · Checkout page' : 'Straight to checkout'}
        </a>
      )}
    </div>
  )
}

export function DetailScreen() {
  const { listings, route, feed } = useApp()
  const byId = useMemo(() => new Map((listings?.showings ?? []).map((s) => [s.id, s])), [listings])
  const s = route.show ? byId.get(route.show) : undefined
  if (!s) {
    return (
      <div className="detail">
        <BackBar />
        {!listings || !feed.complete ? (
          <LoadingState />
        ) : (
          <MessageState
            title="Gone."
            body="This event has dropped out of the latest listings."
            primary={{ label: 'Back', onClick: () => goBack({ show: null, sel: null }) }}
          />
        )}
      </div>
    )
  }
  return isMusic(s) ? <GigDetail s={s} /> : <FilmDetail s={s} />
}

function FilmDetail({ s }: { s: Showing }) {
  const { listings, route, now, today } = useApp()
  const showtimes = useMemo(() => (s.isRun ? [] : Q.showtimes(listings!.showings, s, now)), [listings, s, now])
  const all = showtimes.flatMap((d) => d.items.map((i) => i.showing))
  const selectedId = route.sel ?? s.id
  const inList = all.some((x) => x.id === selectedId)
  const selected = all.find((x) => x.id === selectedId) ?? s
  const byVenue = new Map<string, Showing[]>()
  for (const x of all) byVenue.set(x.venue, [...(byVenue.get(x.venue) ?? []), x])
  const blurb = blurbFor(listings!, s)
  const runText = runLabel(s, today)

  return (
    <div className="detail">
      <BackBar />
      <div className="detail-body">
        <div className="detail-top">
          <Poster url={s.imageUrl} seed={artSeed(s)} width={168} height={252} />
          <dl className="data-items">
            <DataItem term="Type" value={s.category !== 'FILM' ? CATEGORY_LABEL[s.category] : null} />
            <DataItem term="With" value={s.lineup.join(', ')} />
            <DataItem term="Runtime" value={s.runtimeMinutes !== null ? `${s.runtimeMinutes} min` : null} />
            <DataItem term="Certificate" value={s.certificate} />
            <DataItem term={s.category === 'FILM' ? 'Format' : 'Notes'} value={s.displayTags.join(' · ')} />
            <DataItem term="Price" value={selected.price} />
            {s.isRun ? (
              <DataItem term="Run" value={`${F.relativeDay(s.listingDate, today)} – ${F.relativeDay(s.runEnd!, today)}`} now />
            ) : (
              <DataItem
                term={selected.id === s.id ? 'Showing' : 'Selected'}
                value={`${F.relativeDay(selected.listingDate, today)} ${F.time(selected.start)}`}
                now
              />
            )}
          </dl>
        </div>
        <div className="detail-title">
          <FitText text={s.title} className="t-detailTitle" maxSize={76} lineHeight={0.86} maxLines={4} />
        </div>
        <Blurb text={blurb} />
        <div style={{ marginTop: 26 }}>
          {s.isRun ? (
            <>
              <SectionHeading title="Performances" note={s.venue} />
              <p className="t-monoBody muted" style={{ margin: 0, padding: '14px 0' }}>
                {s.venue} only lists the run dates for this production, not individual performance times. Check their site for
                times.
              </p>
            </>
          ) : (
            <>
              <SectionHeading
                title={s.category === 'FILM' ? 'Showtimes' : 'Performances'}
                note={`${all.length} across ${F.count(byVenue.size, 'venue')}`}
              />
              {[...byVenue].map(([venue, shows]) => {
                const screens = new Set(shows.map(screen))
                const one = screens.size === 1 ? [...screens][0] : null
                return (
                  <div key={venue} className="venue-block">
                    <div className="venue-block-head">
                      <h3 className="t-listTitle" style={{ margin: 0, fontSize: 21 }}>
                        {venue}
                      </h3>
                      {one && <span className="t-meta muted">{one}</span>}
                    </div>
                    <div className="chips-grid">
                      {shows.map((x) => (
                        <button
                          key={x.id}
                          className={`time-chip ${x.isSoldOut ? 'sold' : ''}`}
                          aria-pressed={inList && x.id === selectedId}
                          onClick={() => navigate({ sel: x.id })}
                        >
                          <span className="t-tag">{x.isSoldOut ? 'Sold out' : F.relativeDay(x.listingDate, today)}</span>
                          <span className="t-time">{F.time(x.start)}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </>
          )}
        </div>
        <SourceLine s={selected} />
      </div>
      <BookBar
        s={selected}
        sub={s.isRun ? `${s.venue} · ${runText}` : `${selected.venue} · ${F.relativeDay(selected.listingDate, today)} ${F.time(selected.start)}`}
      />
    </div>
  )
}

function GigDetail({ s }: { s: Showing }) {
  const { listings, today } = useApp()
  const blurb = blurbFor(listings!, s)
  const doors = s.doors ? F.time(s.doors) : null
  const start = `${F.relativeDay(s.listingDate, today)} ${F.time(s.start)}`
  return (
    <div className="detail">
      <BackBar />
      <div className="detail-body">
        {s.imageUrl ? (
          <>
            <Poster url={s.imageUrl} seed={artSeed(s)} width="100%" height="auto" />
            <dl className="data-items gig-cols">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <GigItem term="Doors" value={doors} />
                <GigItem term="Price" value={s.price} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <GigItem term="Start" value={start} now />
                <GigItem term="Genre" value={s.genre} />
              </div>
            </dl>
          </>
        ) : (
          <div className="detail-top">
            <Poster url={null} seed={artSeed(s)} width={168} height={168} />
            <dl className="data-items">
              <GigItem term="Doors" value={doors} />
              <GigItem term="Start" value={start} now />
              <GigItem term="Price" value={s.price} />
              <GigItem term="Genre" value={s.genre} />
            </dl>
          </div>
        )}
        <div className="detail-title" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <FitText text={s.title} className="t-detailTitle" maxSize={76} lineHeight={0.86} maxLines={4} />
          <span className="t-monoLabel muted">
            {s.venue} · {F.longDay(s.listingDate)}
          </span>
        </div>
        <Blurb text={blurb} />
        <div className="lineup">
          <SectionHeading title="Lineup" note={s.lineup.length ? F.count(s.lineup.length, 'act') : null} />
          {s.lineup.length === 0 ? (
            <p className="t-monoBody muted" style={{ margin: 0, padding: '14px 0' }}>
              Lineup not listed.
            </p>
          ) : (
            <>
              <div className="lineup-act" style={{ paddingTop: 14 }}>
                <span className="t-tag accent">Headliner</span>
                <div className="t-dayHeader" style={{ marginTop: 4 }}>
                  {s.lineup[0]}
                </div>
              </div>
              {s.lineup.slice(1).map((act) => (
                <div key={act} className="lineup-act t-cardTitle">
                  {act}
                </div>
              ))}
            </>
          )}
        </div>
        <SourceLine s={s} />
      </div>
      <BookBar s={s} sub={`${s.venue} · ${start}`} />
    </div>
  )
}
