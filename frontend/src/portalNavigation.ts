import type { SectionOption } from './components/SectionNavigation'

export type PortalSection = 'home' | 'health' | 'visits' | 'results' | 'care' | 'preferences'

export const portalSections: SectionOption<PortalSection>[] = [
  { id: 'home', label: 'Home' },
  { id: 'health', label: 'Health summary' },
  { id: 'visits', label: 'Appointments & visits' },
  { id: 'results', label: 'Results & referrals' },
  { id: 'care', label: 'Care plan' },
  { id: 'preferences', label: 'Preferences' },
]

export const portalSectionDescriptions: Record<PortalSection, string> = {
  home: 'Find your next appointment and choose what you want to do.',
  health: 'Review your health conditions, medications, allergies and recorded vital signs.',
  visits: 'Review scheduled appointments, visit summaries and appointment change requests.',
  results: 'Review laboratory requests, released results and specialist referrals.',
  care: 'Follow your care goals and progress.',
  preferences: 'Choose how you prefer to receive clinic updates.',
}
