import PortalAppointments from './PortalAppointments'
import PortalProblemList from './PortalProblemList'
import PortalMedications from './PortalMedications'
import PortalAllergies from './PortalAllergies'
import PortalVitals from './PortalVitals'
import PortalVisits from './PortalVisits'
import PortalCareGoals from './PortalCareGoals'
import PortalLabResults from './PortalLabResults'
import PortalReferrals from './PortalReferrals'
import PortalCommunicationPreferences from './PortalCommunicationPreferences'
import './PatientPortalPreview.css'

export default function PatientPortal() {
  return (
    <main className="portal-preview">
      <div className="portal-shell">
        <header className="portal-header">
          <p className="portal-eyebrow">Patient portal</p>
          <h1>My health summary</h1>
          <p>View your appointments, finalized visits, conditions, medications, allergies, recent vitals, care goals, lab requests, released results, and referrals recorded in your chart.</p>
        </header>
        <p className="portal-disclaimer" role="note">
          This portfolio portal uses fictional records only. Clinical information is
          read-only; communication preferences can be changed in this demo. Do not
          use it for real patient information or medical decisions.
        </p>
        <div className="portal-grid">
          <PortalAppointments />
          <PortalVisits />
          <PortalProblemList />
          <PortalMedications />
          <PortalAllergies />
          <PortalVitals />
          <PortalCareGoals />
          <PortalLabResults />
          <PortalReferrals />
          <PortalCommunicationPreferences />
        </div>
      </div>
    </main>
  )
}
