import { useState, type FormEvent } from 'react'
import { API_BASE_URL, BROWSER_MODE, apiFetch, getApiErrorMessage, setAccessToken } from '../api'
import './StaffSignIn.css'

export type SignedInAccount = {
  id: number
  username: string
  account_type: string
  staff_role: string | null
  patient_id: number | null
}

type SignInProps = {
  mode: 'staff' | 'patient'
  onModeChange: (mode: 'staff' | 'patient') => void
  onSignedIn: (account: SignedInAccount) => void
}

export default function SignIn({ mode, onModeChange, onSignedIn }: SignInProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await signIn(username, password)
  }

  async function signIn(loginName: string, loginPassword: string) {
    if (busy) return
    setError(null)
    setBusy(true)
    try {
      setAccessToken(null)
      const response = await apiFetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginName, password: loginPassword }),
      })
      if (!response.ok) {
        setError(await getApiErrorMessage(response))
        return
      }
      const { access_token } = (await response.json()) as { access_token: string }
      setAccessToken(access_token)
      const me = await apiFetch(`${API_BASE_URL}/auth/me`)
      if (!me.ok) {
        throw new Error('Could not verify the signed-in account.')
      }
      const account = (await me.json()) as SignedInAccount
      const allowed = mode === 'patient'
        ? account.account_type === 'patient' && account.patient_id !== null
        : account.account_type === 'staff' &&
          ['clinician', 'admin'].includes(account.staff_role ?? '')
      if (!allowed) {
        await apiFetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' })
        throw new Error(`This account does not have access to the ${mode === 'patient' ? 'patient portal' : 'clinical workspace'}.`)
      }
      setPassword('')
      onSignedIn(account)
    } catch (requestError) {
      setAccessToken(null)
      setError(requestError instanceof Error ? requestError.message : 'Sign-in failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="sign-in-page">
      <section className="sign-in-panel" aria-labelledby="sign-in-title">
        <p className="sign-in-eyebrow">Primary Care EMR</p>
        <h1 id="sign-in-title">{mode === 'patient' ? 'Patient sign in' : 'Staff sign in'}</h1>
        <p>Enter your {mode} account credentials.</p>
        {BROWSER_MODE && (
          <div className="account-choices" aria-label="Available accounts">
            {(mode === 'staff'
              ? [{ username: 'admin', name: 'Administrator' }, { username: 'clinician', name: 'Clinician' }]
              : [{ username: 'jordan.lee', name: 'Jordan Lee' }, { username: 'maria.thompson', name: 'Maria Thompson' }]
            ).map((choice) => (
              <button key={choice.username} type="button" disabled={busy}
                onClick={() => void signIn(choice.username, 'Welcome-EMR-2026')}>
                Sign in as {choice.name}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="account-username">Username</label>
          <input
            id="account-username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
          <label htmlFor="account-password">Password</label>
          <input
            id="account-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && <p role="alert" className="form-error">{error}</p>}
          <button type="submit" disabled={busy}>
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        {busy && <p role="status">Connecting to your workspace…</p>}
        <button
          type="button"
          className="sign-in-switch"
          onClick={() => onModeChange(mode === 'staff' ? 'patient' : 'staff')}
        >
          {mode === 'staff' ? 'Go to patient sign in' : 'Go to staff sign in'}
        </button>
      </section>
    </main>
  )
}
