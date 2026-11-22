import PortalAppointments from './PortalAppointments'
import PortalProblemList from './PortalProblemList'
import PortalMedications from './PortalMedications'
import PortalAllergies from './PortalAllergies'
import './PatientPortalPreview.css'

export default function PatientPortal() {
  return (
    <main className="portal-preview">
      <div className="portal-shell">
        <header className="portal-header">
          <p className="portal-eyebrow">Patient portal</p>
          <h1>My health summary</h1>
          <p>View your appointments, conditions, medications, and allergies recorded in your chart.</p>
        </header>
        <p className="portal-disclaimer" role="note">
          This read-only portfolio portal uses fictional records only. It is not for
          real patient information or medical decisions.
        </p>
        <div className="portal-grid">
          <PortalAppointments />
          <PortalProblemList />
          <PortalMedications />
          <PortalAllergies />
        </div>
      </div>
    </main>
  )
}
