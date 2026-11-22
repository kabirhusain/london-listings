import { useLayoutEffect, useRef, useState, type CSSProperties, type MouseEvent, type ReactNode } from 'react'
import { navigate, hrefFor, type Route } from '../../data/route'
import { posterArt } from '../../text/posterArt'

/* ---- Icons: the app's 24-unit stroke icons (Controls.kt) ---- */
type IconProps = { size?: number; className?: string }
const svg = (size: number, children: ReactNode, className?: string) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true" className={className}>
    {children}
  </svg>
)
export const ArrowIcon = ({ size = 22, className }: IconProps) =>
  svg(size, <path d="M5 12h13M13 6l6 6-6 6" strokeWidth={2.4} strokeLinecap="square" />, className)
export const ArrowLeftIcon = ({ size = 18, className }: IconProps) =>
  svg(size, <path d="M19 12h-13M11 6l-6 6 6 6" strokeWidth={2.4} strokeLinecap="square" />, className)
export const ArrowUpRightIcon = ({ size = 26, className }: IconProps) =>
  svg(size, <path d="M7 17L17 7M9 7h8v8" strokeWidth={2.4} strokeLinecap="square" />, className)
export const BackArrowIcon = ({ size = 18, className }: IconProps) =>
  svg(size, <path d="M19 12H6M11 6l-6 6 6 6" strokeWidth={2.2} strokeLinecap="square" />, className)
export const CloseIcon = ({ size = 20, stroke = 2, className }: IconProps & { stroke?: number }) =>
  svg(size, <path d="M6 6l12 12M18 6L6 18" strokeWidth={stroke} strokeLinecap="round" />, className)
export const SlidersIcon = ({ size = 16, className }: IconProps) =>
  svg(
    size,
    <g strokeWidth={2} strokeLinecap="round">
      <path d="M3 6h11M19 6h2M3 12h4M11 12h10M3 18h13" />
      <circle cx="16.5" cy="6" r="2.5" />
      <circle cx="9" cy="12" r="2.5" />
      <circle cx="18.5" cy="18" r="2.5" />
    </g>,
    className,
  )
export const SearchIcon = ({ size = 18, className }: IconProps) =>
  svg(
    size,
    <g strokeWidth={2} strokeLinecap="round">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M15.5 15.5L20 20" />
    </g>,
    className,
  )

/* ---- Links that change the view without reloading, but stay real links ---- */
export function NavLink({
  to,
  push = false,
  className,
  style,
  children,
  label,
  current,
  onNavigate,
}: {
  to: Partial<Route>
  push?: boolean
  className?: string
  style?: CSSProperties
  children: ReactNode
  label?: string
  current?: 'page' | 'true' | 'date'
  onNavigate?: () => void
}) {
  const onClick = (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    e.preventDefault()
    navigate(to, { push })
    onNavigate?.()
  }
  return (
    <a href={hrefFor(to)} onClick={onClick} className={className} style={style} aria-label={label} aria-current={current}>
      {children}
    </a>
  )
}

/** A link out of the site (venue pages, ticketing, credits). */
export function ExtLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
    </a>
  )
}

/* ---- Poster (Poster.kt): generated art card, with the venue's image over it when there is one ---- */
export function Poster({ url, seed, width, height }: { url: string | null; seed: string; width: number | string; height?: number | string }) {
  const art = posterArt(seed)
  const [failed, setFailed] = useState(false)
  const w = typeof width === 'number' ? width : 168
  const r = (x: number) => `${Math.round(w * x)}px`
  const stroke = `${Math.max(2, Math.round(w * 0.07))}px solid ${art.fg}`
  const shape: Record<string, CSSProperties> = {
    SUN: { left: r(0.18), top: r(0.66), width: r(0.64), height: r(0.64), borderRadius: '50%', background: art.fg },
    BAND: { left: 0, top: r(0.9), width: '100%', height: r(0.2), background: art.fg },
    STRIPE: { left: r(0.4), top: 0, width: r(0.18), height: '100%', background: art.fg },
    DOT: { left: r(0.54), top: r(0.14), width: r(0.3), height: r(0.3), borderRadius: '50%', background: art.fg },
    RING: { left: r(0.14), top: r(0.4), width: r(0.72), height: r(0.72), borderRadius: '50%', border: stroke },
    SPLIT: { left: 0, top: 0, width: '50%', height: '100%', background: art.fg },
    FRAME: { left: r(0.2), top: r(0.45), width: r(0.6), height: r(0.6), border: stroke },
  }
  return (
    <div
      className="poster"
      style={{
        width,
        height: typeof width === 'number' ? (height ?? width * 1.5) : undefined,
        // A full-width poster (the gig detail) is 16:10.
        aspectRatio: typeof width === 'number' ? undefined : '16 / 10',
        background: art.bg,
      }}
    >
      <div className="shape" style={shape[art.shape]} />
      {url && !failed && (
        <img src={url} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      )}
    </div>
  )
}

/* ---- FitText (FitText.kt): keep the design's size where it fits, step down 2px to a 28px minimum ---- */
let canvas: HTMLCanvasElement | null = null
function measure(text: string, font: string, letterSpacingEm: number, size: number): number {
  canvas ??= document.createElement('canvas')
  const ctx = canvas.getContext('2d')!
  ctx.font = font
  return ctx.measureText(text).width + letterSpacingEm * size * text.length
}

export function FitText({
  text,
  className,
  maxSize,
  weight = 800,
  lineHeight,
  letterSpacingEm = -0.01,
  maxLines = 1,
  minSize = 28,
  as: Tag = 'h1',
}: {
  text: string
  className: string
  maxSize: number
  weight?: number
  lineHeight: number
  letterSpacingEm?: number
  maxLines?: number
  minSize?: number
  as?: 'h1' | 'h2' | 'div'
}) {
  const ref = useRef<HTMLElement>(null)
  const [size, setSize] = useState(maxSize)
  const [width, setWidth] = useState(0)
  const [fontsReady, setFontsReady] = useState(0)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width))
    ro.observe(el)
    document.fonts?.ready.then(() => setFontsReady((n) => n + 1))
    return () => ro.disconnect()
  }, [])

  useLayoutEffect(() => {
    if (!width) return
    const upper = text.toUpperCase()
    const words = upper.split(/\s+/).filter(Boolean)
    let s = maxSize
    for (; s > minSize; s -= 2) {
      const font = `${weight} ${s}px "Barlow Condensed", "Arial Narrow", sans-serif`
      const space = measure(' ', font, letterSpacingEm, s)
      if (Math.max(...words.map((w) => measure(w, font, letterSpacingEm, s))) > width) continue
      let lines = 1
      let line = 0
      for (const w of words) {
        const ww = measure(w, font, letterSpacingEm, s)
        if (line > 0 && line + space + ww > width) {
          lines++
          line = ww
        } else line += (line > 0 ? space : 0) + ww
      }
      if (lines <= maxLines) break
    }
    setSize(Math.max(s, minSize))
  }, [text, width, maxSize, minSize, maxLines, weight, letterSpacingEm, fontsReady])

  return (
    <Tag ref={ref as never} className={className} style={{ fontSize: size, lineHeight, margin: 0, overflowWrap: 'break-word' }}>
      {text}
    </Tag>
  )
}

/* ---- Licence credits: link the domain and the licence named in a source's attribution ---- */
const LICENCES: Record<string, string> = {
  'CC BY 4.0': 'https://creativecommons.org/licenses/by/4.0/',
}
export function Attribution({ text }: { text: string }) {
  const pattern = /(CC BY 4\.0|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|co\.uk|org\.uk|fm|io)\b)/g
  const parts = text.split(pattern)
  return (
    <>
      {parts.map((p, i) =>
        i % 2 === 1 ? (
          <ExtLink key={i} href={LICENCES[p] ?? `https://${p}`}>
            {p}
          </ExtLink>
        ) : (
          p
        ),
      )}
    </>
  )
}
