/**
 * Port of the generated poster art in tonight-in-london ui/components/Poster.kt. The seed picks
 * the colours and shape through Java's String.hashCode, so a title gets the same card on the
 * website as in the Android app.
 */

export type Shape = 'SUN' | 'BAND' | 'STRIPE' | 'DOT' | 'RING' | 'SPLIT' | 'FRAME'
const SHAPES: Shape[] = ['SUN', 'BAND', 'STRIPE', 'DOT', 'RING', 'SPLIT', 'FRAME']

// Colour pairs (background, foreground) from the mock posters in the design handoff.
const PALETTE: [string, string][] = [
  ['#B9A57A', '#2A2622'],
  ['#5C6B61', '#EEE5CF'],
  ['#E9E2D4', '#151413'],
  ['#E46A8B', '#FFE9A8'],
  ['#2C6E8F', '#F1E6D0'],
  ['#2F3B2E', '#C9C2A3'],
  ['#7A1A22', '#E9B44C'],
  ['#24453A', '#E8C873'],
  ['#C9452E', '#F2D7A6'],
  ['#14213D', '#D8D2F0'],
  ['#E5C23A', '#1F4C7A'],
  ['#1E3C8C', '#F05A3C'],
  ['#C04A2A', '#F0E3C8'],
  ['#8C0F1B', '#3B9BB0'],
  ['#3E7C5A', '#F3E7C9'],
  ['#1A1A1A', '#EDEDED'],
  ['#2B2B2B', '#E57B3A'],
]

/** Java's String.hashCode: s[0]*31^(n-1) + … over UTF-16 code units, as a signed 32-bit int. */
export function javaHashCode(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0
  return h
}

export interface PosterArt {
  bg: string
  fg: string
  shape: Shape
}

export function posterArt(seed: string): PosterArt {
  // Kotlin's abs(Int.MIN_VALUE) stays negative (and would crash the app); clamp so we never do.
  const h = Math.abs(javaHashCode(seed)) % 2_147_483_647
  const [bg, fg] = PALETTE[h % PALETTE.length]
  return { bg, fg, shape: SHAPES[Math.floor(h / PALETTE.length) % SHAPES.length] }
}
