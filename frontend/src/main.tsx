import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <aside className="legal-notice" role="note" aria-label="Legal notice">
      <p><strong>NOTICE:</strong> For educational and demonstration purposes only. All provided patient records are fictional. Not approved for clinical use, diagnosis, or treatment. Do not enter real patient information. No orders, referrals, or messages are transmitted to external clinical services. On the public website, interactions remain in the browser.</p>
    </aside>
    <App />
  </StrictMode>,
)
