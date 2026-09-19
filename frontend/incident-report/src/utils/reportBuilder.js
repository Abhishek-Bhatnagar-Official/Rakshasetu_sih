import { generateReportId } from './reportId.js'
import { hasValidCoordinates, normalizeOptionalText } from './validation.js'

export const RAW_REPORT_KEYS = Object.freeze([
  'report_id',
  'source_type',
  'location_text',
  'latitude',
  'longitude',
  'description',
  'affected_people',
  'injured_people',
  'people_trapped',
  'medical_emergency',
  'submitted_at',
])

export function formatSubmittedAt(date = new Date()) {
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function toNullableBoolean(value) {
  if (value === true || value === false) return value
  return null
}

function toNullableNumber(value) {
  if (value === null || value === undefined || value === '') return null
  return value
}

export function buildRawReport(formData, coordinates = {}, options = {}) {
  const latitude = coordinates.latitude ?? formData.latitude ?? null
  const longitude = coordinates.longitude ?? formData.longitude ?? null
  const coordsValid = hasValidCoordinates(latitude, longitude)

  const report = {
    report_id: options.report_id ?? generateReportId(),
    source_type: 'citizen',
    location_text: normalizeOptionalText(formData.location_text),
    latitude: coordsValid ? latitude : null,
    longitude: coordsValid ? longitude : null,
    description: String(formData.description ?? '').trim(),
    affected_people: toNullableNumber(formData.affected_people),
    injured_people: toNullableNumber(formData.injured_people),
    people_trapped: toNullableBoolean(formData.people_trapped),
    medical_emergency: toNullableBoolean(formData.medical_emergency),
    submitted_at: options.submitted_at ?? formatSubmittedAt(),
  }

  return report
}
