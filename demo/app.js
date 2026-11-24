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
    const active = button.dataset.viewTarget === viewName
    button.classList.toggle('is-active', active)
    if (active) button.setAttribute('aria-current', 'page')
    else button.removeAttribute('aria-current')
  })

  if (focus) {
    document.querySelector('#main-content')?.focus({ preventScroll: true })
    window.scrollTo({ top: 0, behavior: 'auto' })
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
function selectChartTab(tab, focus = false) {
  chartTabs.forEach((candidate) => {
    const selected = candidate === tab
    candidate.setAttribute('aria-selected', String(selected))
    candidate.tabIndex = selected ? 0 : -1
  })
  chartPanels.forEach((panel) => {
    panel.hidden = panel.dataset.chartPanel !== tab.dataset.chartTab
  })
  if (focus) tab.focus()
}

chartTabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectChartTab(tab))
  tab.addEventListener('keydown', (event) => {
    let next
    if (event.key === 'ArrowRight') next = (index + 1) % chartTabs.length
    else if (event.key === 'ArrowLeft') next = (index - 1 + chartTabs.length) % chartTabs.length
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = chartTabs.length - 1
    else return
    event.preventDefault()
    selectChartTab(chartTabs[next], true)
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
  lifecycleButton.textContent = lifecycleActive ? 'Archive chart' : 'Reactivate chart'
  const chip = document.querySelector('#lifecycle-chip')
  chip.textContent = lifecycleActive ? 'Active' : 'Archived'
  chip.classList.toggle('active', lifecycleActive)
  chip.classList.toggle('resolved', !lifecycleActive)
  document.querySelector('#lifecycle-detail').textContent = lifecycleActive
    ? 'Reactivated'
    : 'Archived'
  lifecycleStatus.textContent = lifecycleActive
    ? 'Chart status changed to active.'
    : 'Chart status changed to archived.'
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
    requestStatus.textContent = `${label.charAt(0).toUpperCase() + label.slice(1)} request selected. Nothing was sent and the appointment was not changed.`
    requestPanel.hidden = true
    requestButton.setAttribute('aria-expanded', 'false')
    requestButton.focus()
  })
})

const preferencesForm = document.querySelector('#preferences-form')
const preferencesStatus = document.querySelector('#preferences-status')
const storageKey = 'primary-care-emr-demo-preferences'

function restorePreferences() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey))
    if (!saved) return
    const contact = [...preferencesForm.querySelectorAll('input[name="contact"]')].find((input) => input.value === saved.contact)
    if (contact) contact.checked = true
    const appointments = preferencesForm?.querySelector('input[name="appointments"]')
    const care = preferencesForm?.querySelector('input[name="care"]')
    if (appointments) appointments.checked = Boolean(saved.appointments)
    if (care) care.checked = Boolean(saved.care)
  } catch {
    // Storage can be unavailable or contain invalid data; retain the defaults.
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
  try {
    localStorage.setItem(storageKey, JSON.stringify(preferences))
    preferencesStatus.textContent = 'Preferences saved in this browser. No message will be sent.'
  } catch {
    preferencesStatus.textContent = 'Browser storage is unavailable. Preferences were not saved or sent.'
  }
})

restorePreferences()
