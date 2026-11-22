// Signed-in patients use their authenticated session, never a browser-supplied chart ID.
export function portalReferralsPath(patientId?: number): string {
  return patientId === undefined
    ? '/portal/referrals'
    : `/patients/${patientId}/portal-preview/referrals`
}
