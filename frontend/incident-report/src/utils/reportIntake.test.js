import { beforeEach, describe, expect, it } from 'vitest'
import { buildRawReport, RAW_REPORT_KEYS } from './reportBuilder.js'
import { generateReportId, resetReportIdSequence } from './reportId.js'
import { LOCATION_REQUIRED_MESSAGE, validateReportInput } from './validation.js'

function submitReport(input, coordinates, options) {
  const result = validateReportInput(input)
  if (!result.valid) {
    return { ok: false, errors: result.errors, raw_report: null }
  }
  return {
    ok: true,
    errors: {},
    raw_report: buildRawReport(result.parsed, coordinates ?? result.parsed, options),
  }
}

describe('Module 1 report intake', () => {
  beforeEach(() => {
    resetReportIdSequence(0)
  })

  it('Test 1 — normal report maps structured fields correctly', () => {
    const result = submitReport(
      {
        location_text: 'Raj Nagar Extension, Ghaziabad',
        latitude: null,
        longitude: null,
        description:
          'Water has entered several houses. Around 30 people are trapped and two people are injured.',
        affected_people: 30,
        injured_people: 2,
        people_trapped: true,
        medical_emergency: true,
      },
      undefined,
      { report_id: 'R001', submitted_at: '2026-09-05T14:32:15' },
    )

    expect(result.ok).toBe(true)
    expect(result.raw_report.people_trapped).toBe(true)
    expect(result.raw_report.medical_emergency).toBe(true)
    expect(result.raw_report.affected_people).toBe(30)
    expect(result.raw_report.injured_people).toBe(2)
    expect(result.raw_report.source_type).toBe('citizen')
    expect(result.raw_report.location_text).toBe('Raj Nagar Extension, Ghaziabad')
    expect(result.raw_report.latitude).toBe(null)
    expect(result.raw_report.longitude).toBe(null)
    expect(Object.keys(result.raw_report)).toEqual([...RAW_REPORT_KEYS])
  })

  it('Test 2 — missing optional fields still produce a valid report', () => {
    const result = submitReport({
      location_text: 'Agra',
      description: 'Heavy waterlogging near the main road.',
      affected_people: null,
      injured_people: null,
      people_trapped: null,
      medical_emergency: null,
      latitude: null,
      longitude: null,
    })

    expect(result.ok).toBe(true)
    expect(result.raw_report.location_text).toBe('Agra')
    expect(result.raw_report.affected_people).toBe(null)
    expect(result.raw_report.injured_people).toBe(null)
    expect(result.raw_report.people_trapped).toBe(null)
    expect(result.raw_report.medical_emergency).toBe(null)
    expect(result.raw_report.latitude).toBe(null)
    expect(result.raw_report.longitude).toBe(null)
    expect(result.raw_report.source_type).toBe('citizen')
    expect(typeof result.raw_report.report_id).toBe('string')
    expect(typeof result.raw_report.submitted_at).toBe('string')
  })

  it('Test 3 — GPS-enabled report submits without location_text', () => {
    const result = submitReport({
      location_text: '',
      description: 'Building collapse reported near the crossing.',
      affected_people: '',
      injured_people: '',
      people_trapped: null,
      medical_emergency: null,
      latitude: 28.6901,
      longitude: 77.4304,
    })

    expect(result.ok).toBe(true)
    expect(result.raw_report.location_text).toBe(null)
    expect(typeof result.raw_report.latitude).toBe('number')
    expect(typeof result.raw_report.longitude).toBe('number')
    expect(result.raw_report.latitude).toBe(28.6901)
    expect(result.raw_report.longitude).toBe(77.4304)
  })

  it('Test 4 — invalid numeric input is rejected', () => {
    const negative = submitReport({
      location_text: 'Agra',
      description: 'Need help near the flooded street now.',
      affected_people: -5,
      injured_people: -2,
    })

    expect(negative.ok).toBe(false)
    expect(negative.errors.affected_people).toBeTruthy()
    expect(negative.errors.injured_people).toBeTruthy()

    const relationship = submitReport({
      location_text: 'Agra',
      description: 'Need help near the flooded street now.',
      affected_people: 2,
      injured_people: 5,
    })

    expect(relationship.ok).toBe(false)
    expect(relationship.errors.injured_people).toMatch(/cannot exceed affected people/i)
  })

  it('Test 5 — missing location is rejected', () => {
    const result = submitReport({
      location_text: '',
      description: 'Need immediate help at this location.',
      latitude: null,
      longitude: null,
    })

    expect(result.ok).toBe(false)
    expect(result.errors.location).toBe(LOCATION_REQUIRED_MESSAGE)
  })

  it('Test 6 — short description is rejected', () => {
    const result = submitReport({
      location_text: 'Agra',
      description: 'Help',
    })

    expect(result.ok).toBe(false)
    expect(result.errors.description).toBeTruthy()
  })

  it('generates unique sequential report IDs', () => {
    expect(generateReportId()).toBe('R001')
    expect(generateReportId()).toBe('R002')
    expect(generateReportId()).toBe('R003')
  })

  it('does not add Module 2 interpretation fields', () => {
    const { raw_report } = submitReport({
      location_text: 'Agra',
      description: 'Heavy waterlogging near the main road.',
    })

    const forbidden = [
      'incident_type',
      'severity_indicators',
      'priority_score',
      'priority_level',
      'resource_requirements',
      'recommended_resources',
      'allocation_plan',
    ]

    for (const key of forbidden) {
      expect(raw_report).not.toHaveProperty(key)
    }
  })
})
