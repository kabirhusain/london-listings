// Fonts, self-hosted (SIL OFL 1.1; see the Credits page and third-party-licenses.txt).
// Only the weights the design uses; each file covers every subset, and browsers fetch
// only the subsets a page needs.
import '@fontsource/barlow/400.css'
import '@fontsource/barlow/500.css'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import '@fontsource/barlow-condensed/800.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/600.css'
import './ui/theme.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { startFeed } from './data/feed'
import { initRoute } from './data/route'
import { App } from './ui/App'

history.scrollRestoration = 'manual'
initRoute()
startFeed()
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
