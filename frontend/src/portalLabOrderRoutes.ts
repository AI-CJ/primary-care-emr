// Patient accounts use their authenticated session, never a chart ID supplied by the browser.
export function portalLabOrdersPath(patientId?: number): string {
  return patientId === undefined
    ? '/portal/lab-orders'
    : `/patients/${patientId}/portal-preview/lab-orders`
}
