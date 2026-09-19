export const MIN_DESCRIPTION_LENGTH = 10
export const LOCATION_REQUIRED_MESSAGE =
  'Please provide a location or allow access to your current location.'

export function isValidLatitude(latitude) {
  return typeof latitude === 'number' && Number.isFinite(latitude) && latitude >= -90 && latitude <= 90
}

export function isValidLongitude(longitude) {
  return (
    typeof longitude === 'number' &&
    Number.isFinite(longitude) &&
    longitude >= -180 &&
    longitude <= 180
  )
}

export function hasValidCoordinates(latitude, longitude) {
  return isValidLatitude(latitude) && isValidLongitude(longitude)
}

export function normalizeOptionalText(value) {
  if (value == null) return null
  const trimmed = String(value).trim()
  return trimmed === '' ? null : trimmed
}

export function parseOptionalNonNegativeInteger(value, fieldLabel) {
  if (value === null || value === undefined || value === '') {
    return { value: null, error: null }
  }

  const asString = String(value).trim()
  if (asString === '') {
    return { value: null, error: null }
  }

  if (!/^\d+$/.test(asString)) {
    return {
      value: null,
      error: `${fieldLabel} must be a whole number of 0 or more.`,
    }
  }

  const parsed = Number.parseInt(asString, 10)
  if (!Number.isInteger(parsed) || parsed < 0) {
    return {
      value: null,
      error: `${fieldLabel} must be a whole number of 0 or more.`,
    }
  }

  return { value: parsed, error: null }
}

export function validateReportInput(input) {
  const errors = {}
  const locationText = normalizeOptionalText(input.location_text)
  const latitude = input.latitude ?? null
  const longitude = input.longitude ?? null

  const coordsPresent = latitude !== null || longitude !== null
  if (coordsPresent && !hasValidCoordinates(latitude, longitude)) {
    errors.location = 'Captured coordinates are invalid. Please try again or enter a location.'
  }

  if (!locationText && !hasValidCoordinates(latitude, longitude)) {
    errors.location = LOCATION_REQUIRED_MESSAGE
  }

  const description = typeof input.description === 'string' ? input.description.trim() : ''
  if (!description || description.length < MIN_DESCRIPTION_LENGTH) {
    errors.description = `Please describe what is happening in at least ${MIN_DESCRIPTION_LENGTH} characters.`
  }

  const affected = parseOptionalNonNegativeInteger(input.affected_people, 'Approx. affected people')
  const injured = parseOptionalNonNegativeInteger(input.injured_people, 'Approx. injured people')

  if (affected.error) {
    errors.affected_people = affected.error
  }
  if (injured.error) {
    errors.injured_people = injured.error
  }

  if (
    affected.error == null &&
    injured.error == null &&
    affected.value !== null &&
    injured.value !== null &&
    injured.value > affected.value
  ) {
    errors.injured_people = 'Injured people cannot exceed affected people.'
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
    parsed: {
      location_text: locationText,
      latitude: hasValidCoordinates(latitude, longitude) ? latitude : null,
      longitude: hasValidCoordinates(latitude, longitude) ? longitude : null,
      description,
      affected_people: affected.error ? null : affected.value,
      injured_people: injured.error ? null : injured.value,
      people_trapped: input.people_trapped ?? null,
      medical_emergency: input.medical_emergency ?? null,
    },
  }
}
