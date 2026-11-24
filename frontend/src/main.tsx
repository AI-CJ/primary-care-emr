import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BROWSER_MODE } from './api'

async function resetDemo() {
  if (!window.confirm('Reset all records, accounts, preferences and activity to their original state? All changes in this tab will be lost.')) return
  const { closeBrowserSession } = await import('./browserApi')
  closeBrowserSession()
  window.location.reload()
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <aside className="legal-notice" role="note" aria-label="Legal notice">
      <p><strong>NOTICE:</strong> For educational and demonstration purposes only. All provided patient records are fictional. Not approved for clinical use, diagnosis, or treatment. Do not enter real patient information or personal credentials. No orders, referrals, or messages are transmitted to external clinical services. {BROWSER_MODE && 'All activity remains in this tab; refreshing, closing the tab, or resetting discards changes.'}</p>
      {BROWSER_MODE && <button type="button" onClick={() => void resetDemo()}>Demo reset</button>}
    </aside>
    <App />
  </StrictMode>,
)
