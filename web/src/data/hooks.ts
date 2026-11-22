import { useEffect, useState, useSyncExternalStore } from 'react'
import { MINUTE } from '../domain/time'

/** The current time, truncated to the minute and ticking exactly on each minute boundary. */
export function useClock(): number {
  const [now, setNow] = useState(() => Math.floor(Date.now() / MINUTE) * MINUTE)
  useEffect(() => {
    let timer: number
    const schedule = () => {
      const t = Date.now()
      timer = window.setTimeout(
        () => {
          setNow(Math.floor(Date.now() / MINUTE) * MINUTE)
          schedule()
        },
        MINUTE - (t % MINUTE) + 50,
      )
    }
    schedule()
    // Timers are throttled in background tabs; catch up when the page is shown again.
    const onShow = () => setNow(Math.floor(Date.now() / MINUTE) * MINUTE)
    document.addEventListener('visibilitychange', onShow)
    return () => {
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', onShow)
    }
  }, [])
  return now
}

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (l) => {
      const m = window.matchMedia(query)
      m.addEventListener('change', l)
      return () => m.removeEventListener('change', l)
    },
    () => window.matchMedia(query).matches,
  )
}

export const WIDE = '(min-width: 900px)'
