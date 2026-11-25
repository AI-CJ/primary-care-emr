import { useEffect, useState, type FormEvent } from 'react'
import { API_BASE_URL, BROWSER_MODE, apiFetch, getApiErrorMessage, setAccessToken } from '../api'
import './StaffSignIn.css'
import { BrandMark, CareIllustration } from './BrandArtwork'
import { WorkspaceIcon } from './WorkspaceIcon'

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
  const [preparation, setPreparation] = useState<'preparing' | 'ready' | 'unavailable'>('preparing')

  useEffect(() => {
    if (!BROWSER_MODE) return
    const controller = new AbortController()
    // Start the tab-local runtime while the sign-in screen is visible. The public
    // root endpoint contains no patient data and does not establish a session.
    async function prepareWorkspace() {
      try {
        const response = await apiFetch(API_BASE_URL + '/', { signal: controller.signal })
        if (!response.ok) throw new Error('Workspace preparation failed.')
        if (!controller.signal.aborted) setPreparation('ready')
      } catch {
        if (!controller.signal.aborted) setPreparation('unavailable')
      }
    }
    void prepareWorkspace()
    return () => controller.abort()
  }, [])

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
    <main className={`sign-in-page sign-in-${mode}`}>
      <div className="sign-in-layout">
      <div className="sign-in-intro">
        <div className="sign-in-brand"><BrandMark /> Primary Care EMR</div>
        <p className="sign-in-kicker">{mode === 'staff' ? 'Clinical workspace' : 'Your patient portal'}</p>
        <p className="sign-in-headline">{mode === 'staff' ? <>Connected care.<br />Clearer workflows.</> : <>Your health.<br />All in one place.</>}</p>
        <p>{mode === 'staff' ? 'Patient records, clinical documentation, and care coordination in one workspace.' : 'Find your appointments, health records and care instructions whenever you need them.'}</p>
        <CareIllustration patient={mode === 'patient'} />
        <div className="sign-in-intro-rule" />
        <p className="sign-in-intro-detail">{mode === 'staff' ? 'Clinical access is based on your account role.' : 'Sign in to see your own health information.'}</p>
      </div>
      <section className="sign-in-panel" aria-labelledby="sign-in-title">
        <p className="sign-in-eyebrow">{mode === 'patient' ? 'Patient portal' : 'Clinical workspace'}</p>
        <h1 id="sign-in-title">{mode === 'patient' ? 'Patient sign in' : 'Staff sign in'}</h1>
        <p className="sign-in-description">{BROWSER_MODE ? 'Choose an account to open your workspace.' : 'Enter your account credentials to continue.'}</p>
        {BROWSER_MODE && (
          <div className="account-choices" role="group" aria-label="Available accounts">
            {(mode === 'staff'
              ? [{ username: 'admin', name: 'Administrator', description: 'Clinical work and chart administration' }, { username: 'clinician', name: 'Clinician', description: 'Patient care and clinic work queues' }]
              : [{ username: 'jordan.lee', name: 'Jordan Lee', description: 'Health record and appointments' }, { username: 'maria.thompson', name: 'Maria Thompson', description: 'Health record and appointments' }]
            ).map((choice) => (
              <button key={choice.username} type="button" disabled={busy} aria-label={'Sign in as ' + choice.name} aria-describedby={'account-description-' + choice.username}
                onClick={() => void signIn(choice.username, 'Welcome-EMR-2026')}>
                <span className="account-choice-icon"><WorkspaceIcon name={mode === 'patient' ? 'person' : choice.username === 'admin' ? 'audit' : 'clinician'} size={24} /></span>
                <span className="account-choice-copy"><strong>{choice.name}</strong><small id={'account-description-' + choice.username}>{choice.description}</small></span>
                <WorkspaceIcon name="arrow" size={18} />
              </button>
            ))}
          </div>
        )}
        {BROWSER_MODE && <p className="sign-in-divider">Or sign in with account credentials</p>}
        <form aria-label="Account credentials" onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="account-username">Username</label>
          <input
            id="account-username"
            autoComplete="username"
            disabled={busy}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
          <label htmlFor="account-password">Password</label>
          <input
            id="account-password"
            type="password"
            autoComplete="current-password"
            disabled={busy}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && <p role="alert" className="form-error">{error}</p>}
          <button type="submit" disabled={busy}>
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
        <p className={'sign-in-status sign-in-status-' + (busy ? 'preparing' : preparation)}
          role="status" aria-atomic="true" hidden={!BROWSER_MODE && !busy}>
          {busy ? (BROWSER_MODE && preparation === 'preparing'
            ? 'Preparing the workspace and checking your account…' : 'Checking your account…')
            : BROWSER_MODE ? preparation === 'preparing' ? 'Preparing the workspace. You can sign in while it loads.'
              : preparation === 'ready' ? 'Workspace ready.'
                : 'Workspace preparation did not complete. If sign-in fails, use Demo reset.' : ''}
        </p>
        <button
          type="button"
          className="sign-in-switch"
          disabled={busy}
          onClick={() => onModeChange(mode === 'staff' ? 'patient' : 'staff')}
        >
          {mode === 'staff' ? 'Switch to patient sign-in' : 'Switch to staff sign-in'}
        </button>
      </section>
      </div>
    </main>
  )
}
