/**
 * Credits and sources. The site is public, so every credit the data and assets need is here:
 * the venues, Clusterflick's CC BY 4.0 credit (with the licence and the changes made),
 * Songkick and DICE, the fonts' licence and the open-source software. Built from the feed's
 * sources, so it stays right as venues are added.
 */
import type { Source } from '../../domain/models'
import { goBack } from '../../data/route'
import { useApp } from '../context'
import { Attribution, BackArrowIcon, CloseIcon, ExtLink } from '../components/basics'
import { useAttributions } from '../components/states'

const REPO = 'https://github.com/kabirhusain/london-listings'

function VenueList({ sources }: { sources: Source[] }) {
  return (
    <ul className="venue-list">
      {sources.map((s) => (
        <li key={s.venue}>
          {s.name}
          {s.via && s.viaUrl && s.via !== 'Clusterflick' && (
            <>
              {' '}
              (<ExtLink href={s.viaUrl}>{s.via}</ExtLink>)
            </>
          )}
        </li>
      ))}
    </ul>
  )
}

export function CreditsScreen() {
  const { listings, wide } = useApp()
  const attributions = useAttributions()
  const sources = [...(listings?.sources ?? [])].sort((a, b) =>
    a.name.toLowerCase().replace(/^the /, '').localeCompare(b.name.toLowerCase().replace(/^the /, '')),
  )
  const via = (name: string) => sources.filter((s) => s.via === name)
  const clusterflick = via('Clusterflick')
  const songkick = via('Songkick')
  const dice = via('DICE')
  const names = (list: Source[]) => list.map((s) => s.name).join(', ')

  return (
    <div>
      <div className="backbar">
        <button onClick={() => goBack({ page: null })} aria-label="Back to listings">
          {wide ? <CloseIcon size={18} /> : <BackArrowIcon />}
          {wide ? 'Close' : 'Listings'}
        </button>
      </div>
      <article className="prose">
        <h1 className="t-emptyTitle" style={{ margin: '8px 0 18px' }}>
          Credits
        </h1>
        <p>
          London Calling lists films, gigs, theatre, comedy and dance at {sources.length || 'about 60'} London venues. It's an
          independent, non-commercial project and isn't affiliated with any of the venues or services below. Times, prices and
          availability change: always check with the venue before you go.
        </p>

        <h2 className="t-sectionTitle">Where the listings come from</h2>
        <p>
          Once a day, a collector reads each venue's own what's-on pages, ticketing system or public feed. The event details,
          descriptions, images, prices and booking links come from the venues (or the services credited below) and remain theirs.
          Each event's buttons take you to the venue's own page to book.
        </p>
        <VenueList sources={sources} />

        {clusterflick.length > 0 && (
          <>
            <h2 className="t-sectionTitle">Clusterflick</h2>
            {attributions
              .filter((a) => /clusterflick/i.test(a))
              .map((a) => (
                <p key={a}>
                  <strong>
                    <Attribution text={a} />
                  </strong>
                </p>
              ))}
            <p>
              Film screenings at {names(clusterflick)} come from{' '}
              <ExtLink href="https://clusterflick.com">Clusterflick</ExtLink>'s open data, used under the{' '}
              <ExtLink href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 licence</ExtLink> (
              <ExtLink href="https://clusterflick.com/data-licence">Clusterflick data licence</ExtLink>).
            </p>
            <p>
              Changes made: the data is reshaped into this site's format, merged with other venues' listings, titles are
              normalised so the same film groups across cinemas, and descriptions are shortened.
            </p>
          </>
        )}

        {attributions
          .filter((a) => !/clusterflick/i.test(a))
          .map((a) => (
            <p key={a}>
              <Attribution text={a} />
            </p>
          ))}

        {(songkick.length > 0 || dice.length > 0) && (
          <>
            <h2 className="t-sectionTitle">Songkick and DICE</h2>
            {songkick.length > 0 && (
              <p>
                Gig listings and images for {names(songkick)} come from their pages on{' '}
                <ExtLink href="https://www.songkick.com">Songkick</ExtLink>, and each event links back to Songkick.
              </p>
            )}
            {dice.length > 0 && (
              <p>
                Gig listings and images for {names(dice)} come from their pages on <ExtLink href="https://dice.fm">DICE</ExtLink>
                , and each event links back to DICE.
              </p>
            )}
          </>
        )}

        <h2 className="t-sectionTitle">Images and descriptions</h2>
        <p>
          Posters and photos are shown from the venues' and ticketing services' own servers, and belong to them or to the films'
          and artists' distributors. Where there's no image, the coloured card is generated by this site. If you own something
          shown here and want it changed or removed, please{' '}
          <ExtLink href={`${REPO}/issues`}>open an issue on GitHub</ExtLink>.
        </p>

        <h2 className="t-sectionTitle">Fonts</h2>
        <ul>
          <li>
            <ExtLink href="https://github.com/jpt/barlow">Barlow and Barlow Condensed</ExtLink>, © 2017 The Barlow Project
            Authors
          </li>
          <li>
            <ExtLink href="https://github.com/JetBrains/JetBrainsMono">JetBrains Mono</ExtLink>, © 2020 The JetBrains Mono Project
            Authors
          </li>
        </ul>
        <p>
          Both are used under the <ExtLink href="https://openfontlicense.org">SIL Open Font License 1.1</ExtLink>.
        </p>

        <h2 className="t-sectionTitle">Software</h2>
        <p>
          Built with <ExtLink href="https://react.dev">React</ExtLink> and <ExtLink href="https://vite.dev">Vite</ExtLink>. The
          full licence texts for the code and fonts included in this site are in{' '}
          <a href="third-party-licenses.txt">third-party-licenses.txt</a>.
        </p>

        <h2 className="t-sectionTitle">Data and source code</h2>
        <p>
          The collector and this website are on <ExtLink href={REPO}>GitHub</ExtLink>. The combined listings are published as{' '}
          <a href="listings.json">listings.json</a>, and <a href="status.html">the status page</a> shows how each venue's last
          update went.
        </p>
      </article>
    </div>
  )
}
