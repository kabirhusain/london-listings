import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join, sep } from 'node:path'

/**
 * Writes third-party-licenses.txt next to the built site: the licence text of every
 * npm package whose code, CSS or font files end up in the bundle (React's MIT notice,
 * the fonts' SIL Open Font Licence, ...). Both licences require the notice to travel
 * with the files, and the Credits page links to it.
 */
function thirdPartyLicenses(): Plugin {
  const packages = new Map<string, string>() // name -> package dir
  const packageOf = (id: string): [string, string] | null => {
    const clean = id.split('?')[0].replace(/^\0/, '')
    const i = clean.lastIndexOf(`${sep}node_modules${sep}`)
    if (i < 0) return null
    const rest = clean.slice(i + 14).split(sep)
    const name = rest[0].startsWith('@') ? `${rest[0]}/${rest[1]}` : rest[0]
    return [name, join(clean.slice(0, i + 14), ...name.split('/'))]
  }
  return {
    name: 'third-party-licenses',
    apply: 'build',
    transform(_code, id) {
      const pkg = packageOf(id)
      if (pkg) packages.set(pkg[0], pkg[1])
      return null
    },
    generateBundle() {
      const sections = [...packages.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([name, dir]) => {
        const meta = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'))
        const file = existsSync(dir) ? readdirSync(dir).find((f) => /^(licen[cs]e|copying)/i.test(f)) : undefined
        const text = file ? readFileSync(join(dir, file), 'utf8').trim() : `License: ${meta.license ?? 'see package'}`
        const home = meta.homepage ?? (typeof meta.repository === 'string' ? meta.repository : meta.repository?.url) ?? ''
        return `${name} ${meta.version} (${meta.license ?? 'unknown'})\n${home}\n\n${text}`
      })
      const header =
        'London Calling website: third-party software and fonts\n' +
        'These packages are included in the website. Their licences follow.\n'
      this.emitFile({
        type: 'asset',
        fileName: 'third-party-licenses.txt',
        source: [header, ...sections].join(`\n\n${'='.repeat(72)}\n\n`) + '\n',
      })
    },
  }
}

export default defineConfig({
  // Served from https://kabirhusain.github.io/london-listings/, so keep every URL relative.
  base: './',
  plugins: [react(), thirdPartyLicenses()],
  build: { target: 'es2022', sourcemap: false },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
} as never)
