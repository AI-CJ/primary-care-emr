export type StaffDestination = 'patients' | 'schedule' | 'past' | 'requests' | 'labs' | 'results' | 'referrals' | 'goals' | 'followups' | 'audit'

export const staffDestinationLabels: Record<StaffDestination, string> = {
  patients: 'Patients', schedule: 'Clinic Schedule', past: 'Past Appointments',
  requests: 'Appointment Requests', labs: 'Pending Labs', results: 'Results to Release',
  referrals: 'Pending Referrals', goals: 'Active Care Goals', followups: 'Open Follow-ups',
  audit: 'Audit activity',
}
