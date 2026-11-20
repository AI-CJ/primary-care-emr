import { useState, type FormEvent } from 'react'
import { API_BASE_URL, apiFetch, getApiErrorMessage, setAccessToken } from '../api'
import './StaffSignIn.css'

export type SignedInAccount = {
  id: number
  username: string
  account_type: string
  staff_role: string | null
  patient_id: number | null
}

type StaffSignInProps = {
  onSignedIn: (account: SignedInAccount) => void
}

export default function StaffSignIn({ onSignedIn }: StaffSignInProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
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
      if (account.account_type !== 'staff' ||
          !['clinician', 'admin'].includes(account.staff_role ?? '')) {
        await apiFetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' })
        throw new Error('This account does not have access to the clinical workspace.')
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
        <h1 id="sign-in-title">Staff sign in</h1>
        <p>Use a synthetic staff account for this portfolio demo.</p>
        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="staff-username">Username</label>
          <input
            id="staff-username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
          <label htmlFor="staff-password">Password</label>
          <input
            id="staff-password"
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
      </section>
    </main>
  )
}
