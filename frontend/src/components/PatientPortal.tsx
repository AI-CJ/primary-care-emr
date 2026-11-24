import { useState } from 'react'
import SectionNavigation from './SectionNavigation'
import { type PortalSection, portalSections, portalSectionDescriptions } from '../portalNavigation'
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
import PortalAppointmentChangeRequests from './PortalAppointmentChangeRequests'
import './PatientPortalPreview.css'

export default function PatientPortal() {
  const [section, setSection] = useState<PortalSection>('health')
  const [visited, setVisited] = useState<PortalSection[]>(['health'])

  function navigate(next: PortalSection) {
    setSection(next)
    setVisited((current) => current.includes(next) ? current : [...current, next])
  }

  return (
    <main className="portal-preview patient-workspace">
      <div className="portal-shell">
        <header className="portal-header">
          <p className="portal-eyebrow">Patient portal</p>
          <h1>My health summary</h1>
          <p>Access your health record and manage your appointments in one place.</p>
        </header>
        <SectionNavigation label="Patient portal sections" options={portalSections} current={section} onChange={navigate} />
        <div className="portal-section-heading">
          <h2>{portalSections.find((item) => item.id === section)?.label}</h2>
          <p>{portalSectionDescriptions[section]}</p>
        </div>
        {visited.includes('health') && <div className="portal-grid" hidden={section !== 'health'}>
          <PortalProblemList />
          <PortalMedications />
          <PortalAllergies />
          <PortalVitals />
        </div>}
        {visited.includes('visits') && <div className="portal-grid" hidden={section !== 'visits'}>
          <PortalAppointments />
          <PortalAppointmentChangeRequests />
          <PortalVisits />
        </div>}
        {visited.includes('results') && <div className="portal-grid" hidden={section !== 'results'}>
          <PortalLabResults />
          <PortalReferrals />
        </div>}
        {visited.includes('care') && <div className="portal-grid" hidden={section !== 'care'}>
          <PortalCareGoals />
        </div>}
        {visited.includes('preferences') && <div className="portal-grid" hidden={section !== 'preferences'}>
          <PortalCommunicationPreferences />
        </div>}
      </div>
    </main>
  )
}
