const STORAGE_KEY = 'jobfit_demo_access_code'

export const DEMO_ACCESS_REVOKED_EVENT = 'jobfit-demo-access-revoked'

export function isDemoAccessRequired() {
  return String(import.meta.env.VITE_DEMO_ACCESS_REQUIRED || '').toLowerCase() === 'true'
}

export function getDemoAccessCode() {
  if (!isDemoAccessRequired()) return ''

  try {
    return window.sessionStorage.getItem(STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export function storeDemoAccessCode(code) {
  if (!isDemoAccessRequired()) return

  try {
    window.sessionStorage.setItem(STORAGE_KEY, code)
  } catch {
    // Storage can be unavailable in restrictive browser modes. The caller will
    // still keep access for the current in-memory application state.
  }
}

export function clearDemoAccessCode({ notify = false } = {}) {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // There is nothing else to clear when session storage is unavailable.
  }

  if (notify && isDemoAccessRequired()) {
    window.dispatchEvent(new Event(DEMO_ACCESS_REVOKED_EVENT))
  }
}
