import { useEffect, useRef } from 'react'

/** Keep keyboard navigation within a card when its controls are replaced. */
export function useInlineEditorFocus(open: boolean) {
  const containerRef = useRef<HTMLElement>(null)
  const triggerKey = useRef<string | null>(null)
  const wasOpen = useRef(false)

  useEffect(() => {
    const container = containerRef.current
    if (container && open !== wasOpen.current) {
      if (open) {
        container.querySelector<HTMLElement>(
          '[data-editor-initial-focus], form input:not([type="hidden"]):not(:disabled), '
          + 'form select:not(:disabled), form textarea:not(:disabled), form button:not(:disabled)',
        )?.focus()
      } else {
        const trigger = Array.from(container.querySelectorAll<HTMLElement>('[data-editor-trigger]'))
          .find(element => element.dataset.editorTrigger === triggerKey.current)
        // Saving can temporarily replace a record list with its loading state.
        // Keep focus at the card heading rather than moving it again after the
        // request completes, when the user may already have moved elsewhere.
        const target = trigger ?? container.querySelector<HTMLElement>('h2')
        if (target) {
          if (!trigger) target.tabIndex = -1
          target.focus()
        }
      }
    }
    wasOpen.current = open
  }, [open])

  function rememberTrigger(key: string) {
    triggerKey.current = key
  }

  function returnToHeading() {
    triggerKey.current = null
  }

  return { containerRef, rememberTrigger, returnToHeading }
}
