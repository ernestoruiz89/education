import spanish from './locales/es.json'

// Frappe resolves the user's language before rendering the portal entry point.
export const language = (
  window.education_boot?.language ||
  document.documentElement.lang ||
  'en'
).replace(/_/g, '-')
export const locale = language
const messages = language.split('-')[0].toLowerCase() === 'es' ? spanish : {}

export function __(message) {
  return Object.prototype.hasOwnProperty.call(messages, message)
    ? messages[message]
    : message
}

export function formatNumber(value, options = {}) {
  return new Intl.NumberFormat(locale, options).format(Number(value || 0))
}

export function formatDate(
  value,
  options = { day: 'numeric', month: 'numeric', year: 'numeric' }
) {
  if (!value) return ''
  // Date-only database values describe a local calendar day, not midnight UTC.
  const parts =
    typeof value === 'string' && value.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  const date = parts
    ? new Date(+parts[1], +parts[2] - 1, +parts[3])
    : new Date(value)
  return Number.isNaN(date.getTime())
    ? String(value)
    : new Intl.DateTimeFormat(locale, options).format(date)
}
