import { createContext, useContext } from 'react'
import type { Listings, Source } from '../domain/models'
import type { FeedState } from '../data/feed'
import type { Route } from '../data/route'

export interface AppCtx {
  /** Now, truncated to the minute. */
  now: number
  /** Today's listing date (5am rollover). */
  today: string
  feed: FeedState
  listings: Listings | null
  route: Route
  wide: boolean
  /** Sources by venue slug, for credits. */
  sources: Map<string, Source>
  /** What the detail screen's back link says, from where it was opened. */
  backLabel: string
}

export const Ctx = createContext<AppCtx>(null as never)
export const useApp = () => useContext(Ctx)
