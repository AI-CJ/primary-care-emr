export type LifecycleAccount = {
  account_type: string
  staff_role: string | null
}

export type PatientLifecycleAction = 'archive' | 'reactivate'

export function canManagePatientLifecycle(account: LifecycleAccount | null): boolean {
  return account?.account_type === 'staff' && account.staff_role === 'admin'
}

export function nextPatientLifecycleAction(archivedAt: string | null): PatientLifecycleAction {
  return archivedAt ? 'reactivate' : 'archive'
}

export function patientLifecycleStatus(archivedAt: string | null): 'active' | 'archived' {
  return archivedAt ? 'archived' : 'active'
}
