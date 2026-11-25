import { useEffect, useRef, useState } from 'react'
import SectionNavigation from './SectionNavigation'
import { type PortalSection, portalSections, portalSectionDescriptions } from '../portalNavigation'
import PortalAppointments from './PortalAppointments'
import PortalHome from './PortalHome'
import PortalProblemList from './PortalProblemList'
import PortalMedications from './PortalMedications'
import PortalAllergies from './PortalAllergies'
import PortalVitals from './PortalVitals'
import PortalVisits from './PortalVisits'
import PortalCareGoals from './PortalCareGoals'
import PortalLabResults from './PortalLabResults'
import PortalReferrals from './PortalReferrals'
import { ImagingHistory } from './ChartHistory'
import Immunizations from './Immunizations'
import PortalCommunicationPreferences from './PortalCommunicationPreferences'
import PortalAppointmentChangeRequests from './PortalAppointmentChangeRequests'
import './PatientPortalPreview.css'

export default function PatientPortal() {
  const [section, setSection] = useState<PortalSection>('home')
  const [visited, setVisited] = useState<PortalSection[]>(['home'])
  const pageHeading = useRef<HTMLHeadingElement>(null)
  const sectionHeading = useRef<HTMLHeadingElement>(null)
  const moveFocus = useRef(false)

  useEffect(() => {
    if (!moveFocus.current) return
    moveFocus.current = false
    const heading = section === 'home' ? pageHeading.current : sectionHeading.current
    heading?.focus()
  }, [section])

  function navigate(next: PortalSection) {
    if (next === section) return
    moveFocus.current = true
    setSection(next)
    setVisited((current) => current.includes(next) ? current : [...current, next])
  }

  const navigation = <SectionNavigation label="Patient portal sections" options={portalSections} current={section} onChange={navigate} />

  return (
    <main className="portal-preview patient-workspace">
      <div className="portal-shell">
        <header className="portal-header">
          <p className="portal-eyebrow">Patient portal</p>
          <h1 ref={pageHeading} tabIndex={-1}>{section === 'health' ? 'My health summary' : 'Your patient portal'}</h1>
          <p>Access your health record and manage your appointments in one place.</p>
        </header>
        {section !== 'home' && navigation}
        {section !== 'home' && <div className="portal-section-heading">
          <h2 ref={sectionHeading} tabIndex={-1}>{portalSections.find((item) => item.id === section)?.label}</h2>
          <p>{portalSectionDescriptions[section]}</p>
        </div>}
        {section === 'home' && <PortalHome onNavigate={navigate} navigation={navigation} />}
        {section === 'health' && <div className="portal-grid">
          <PortalProblemList />
          <PortalMedications />
          <PortalAllergies />
          <PortalVitals />
        </div>}
        {visited.includes('visits') && <div className="portal-grid portal-visits-grid" hidden={section !== 'visits'}>
          {section === 'visits' && <PortalAppointments />}
          <PortalAppointmentChangeRequests />
          {section === 'visits' && <PortalVisits />}
        </div>}
        {section === 'results' && <div className="portal-grid portal-results-grid">
          <PortalLabResults />
          <PortalReferrals />
          <ImagingHistory />
        </div>}
        {section === 'immunizations' && <div className="portal-grid"><Immunizations /></div>}
        {section === 'care' && <div className="portal-grid">
          <PortalCareGoals />
        </div>}
        {visited.includes('preferences') && <div className="portal-grid" hidden={section !== 'preferences'}>
          <PortalCommunicationPreferences />
        </div>}
      </div>
    </main>
  )
}
