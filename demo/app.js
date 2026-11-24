const views = [...document.querySelectorAll('[data-view]')]
const modeButtons = [...document.querySelectorAll('[data-mode-target]')]
const modeNavs = [...document.querySelectorAll('[data-mode-nav]')]
const navButtons = [...document.querySelectorAll('[data-view-target]')]

const defaultView = {
  staff: 'staff-overview',
  patient: 'patient-home',
}

function showView(viewName, focus = true) {
  views.forEach((view) => {
    const active = view.dataset.view === viewName
    view.hidden = !active
    view.classList.toggle('is-active', active)
  })

  navButtons.forEach((button) => {
    button.classList.toggle('is-active', button.dataset.viewTarget === viewName)
  })

  if (focus) {
    document.querySelector('#main-content')?.focus({ preventScroll: true })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function setMode(mode) {
  modeButtons.forEach((button) => {
    const active = button.dataset.modeTarget === mode
    button.classList.toggle('is-active', active)
    button.setAttribute('aria-pressed', String(active))
  })

  modeNavs.forEach((nav) => {
    nav.hidden = nav.dataset.modeNav !== mode
  })

  showView(defaultView[mode])
}

modeButtons.forEach((button) => {
  button.addEventListener('click', () => setMode(button.dataset.modeTarget))
})

navButtons.forEach((button) => {
  button.addEventListener('click', () => showView(button.dataset.viewTarget))
})

document.querySelectorAll('[data-go-view]').forEach((button) => {
  button.addEventListener('click', () => {
    const target = button.dataset.goView
    if (target.startsWith('patient-')) setMode('patient')
    if (target.startsWith('staff-')) setMode('staff')
    showView(target)
  })
})

const chartTabs = [...document.querySelectorAll('[data-chart-tab]')]
const chartPanels = [...document.querySelectorAll('[data-chart-panel]')]
chartTabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    chartTabs.forEach((candidate) => {
      candidate.setAttribute('aria-selected', String(candidate === tab))
    })
    chartPanels.forEach((panel) => {
      panel.hidden = panel.dataset.chartPanel !== tab.dataset.chartTab
    })
  })
})

const scheduleFilter = document.querySelector('#schedule-filter')
const scheduleRows = [...document.querySelectorAll('#schedule-body tr')]
scheduleFilter?.addEventListener('input', () => {
  const query = scheduleFilter.value.trim().toLowerCase()
  scheduleRows.forEach((row) => {
    row.hidden = query.length > 0 && !row.dataset.search.includes(query)
  })
})

const lifecycleButton = document.querySelector('#lifecycle-demo')
const lifecycleStatus = document.querySelector('#lifecycle-status')
let lifecycleActive = false
lifecycleButton?.addEventListener('click', () => {
  lifecycleActive = !lifecycleActive
  lifecycleButton.textContent = lifecycleActive ? 'Simulate archive' : 'Simulate reactivation'
  lifecycleStatus.textContent = lifecycleActive
    ? 'Demo chart reactivated. Historical records remain intact.'
    : 'Demo chart archived. New clinical writes would now be blocked.'
})

const requestButton = document.querySelector('#request-change')
const requestPanel = document.querySelector('#request-panel')
const requestStatus = document.querySelector('#request-status')
requestButton?.addEventListener('click', () => {
  requestPanel.hidden = !requestPanel.hidden
  requestButton.setAttribute('aria-expanded', String(!requestPanel.hidden))
})

document.querySelectorAll('[data-request-kind]').forEach((button) => {
  button.addEventListener('click', () => {
    const label = button.dataset.requestKind === 'cancel' ? 'cancellation' : 'rescheduling'
    requestStatus.textContent = `Synthetic ${label} request queued for staff review. The appointment was not changed.`
    requestPanel.hidden = true
  })
})

const preferencesForm = document.querySelector('#preferences-form')
const preferencesStatus = document.querySelector('#preferences-status')
const storageKey = 'primary-care-emr-demo-preferences'

function restorePreferences() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey))
    if (!saved) return
    const contact = preferencesForm?.querySelector(`input[name="contact"][value="${saved.contact}"]`)
    if (contact) contact.checked = true
    const appointments = preferencesForm?.querySelector('input[name="appointments"]')
    const care = preferencesForm?.querySelector('input[name="care"]')
    if (appointments) appointments.checked = Boolean(saved.appointments)
    if (care) care.checked = Boolean(saved.care)
  } catch {
    localStorage.removeItem(storageKey)
  }
}

preferencesForm?.addEventListener('submit', (event) => {
  event.preventDefault()
  const formData = new FormData(preferencesForm)
  const preferences = {
    contact: formData.get('contact'),
    appointments: formData.has('appointments'),
    care: formData.has('care'),
  }
  localStorage.setItem(storageKey, JSON.stringify(preferences))
  preferencesStatus.textContent = 'Demo preferences saved in this browser. No message will be sent.'
})

restorePreferences()
