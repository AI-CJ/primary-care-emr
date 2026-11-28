import { Component, Suspense, createRef, useLayoutEffect, type ReactNode } from 'react'
import { BROWSER_MODE } from '../api'
import './ScreenBoundary.css'

type BoundaryProps = {
  children: ReactNode
  resetKey: string
}

class ScreenErrorBoundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false }
  errorHeading = createRef<HTMLHeadingElement>()

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch() {
    this.errorHeading.current?.focus()
  }

  componentDidUpdate(previous: BoundaryProps) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey) {
      this.setState({ failed: false })
    }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="screen-loading">
        <section role="alert">
          <h1 ref={this.errorHeading} tabIndex={-1}>This screen could not be loaded</h1>
          <p>Check your connection, then reload the application to try again.</p>
          <p>{BROWSER_MODE
            ? 'Reloading resets all changes made in this demo tab.'
            : 'Reloading discards unsaved form changes.'}</p>
          <button type="button" className="secondary-action-button" onClick={() => {
            const message = BROWSER_MODE
              ? 'Reload and reset all changes in this demo tab?'
              : 'Reload and discard unsaved form changes?'
            if (window.confirm(message)) window.location.reload()
          }}>Reload application</button>
        </section>
      </main>
    )
  }
}

function RevealedScreen({ children, onReady }: { children: ReactNode; onReady?: () => void }) {
  // Layout effects run when Suspense reveals the screen, after its heading exists.
  useLayoutEffect(() => { onReady?.() }, [onReady])
  return children
}

export default function ScreenBoundary({ children, resetKey, onReady }: BoundaryProps & { onReady?: () => void }) {
  return (
    <ScreenErrorBoundary resetKey={resetKey}>
      <Suspense fallback={<main className="screen-loading" aria-label="Loading workspace">
        <p role="status">Loading workspace…</p>
      </main>}>
        <RevealedScreen onReady={onReady}>{children}</RevealedScreen>
      </Suspense>
    </ScreenErrorBoundary>
  )
}
