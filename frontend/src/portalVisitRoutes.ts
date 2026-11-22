// Patient accounts must use their authenticated session, never a chart ID from the browser.
export function portalVisitsPath(patientId?: number): string {
  return patientId === undefined
    ? '/portal/visits'
    : `/patients/${patientId}/portal-preview/visits`
}
