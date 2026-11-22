import PortalAppointments from './PortalAppointments'
import './PatientPortalPreview.css'

export default function PatientPortal() {
  return (
    <main className="portal-preview">
      <div className="portal-shell">
        <header className="portal-header">
          <p className="portal-eyebrow">Patient portal</p>
          <h1>My appointments</h1>
          <p>View upcoming visits and recent appointment history.</p>
        </header>
        <p className="portal-disclaimer" role="note">
          This read-only portfolio portal uses fictional records only. It is not for
          real patient information or medical decisions.
        </p>
        <div className="portal-grid">
          <PortalAppointments />
        </div>
      </div>
    </main>
  )
}
