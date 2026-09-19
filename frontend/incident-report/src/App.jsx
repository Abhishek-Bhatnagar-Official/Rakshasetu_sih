import { useState } from 'react'
import BooleanSelector from './components/BooleanSelector.jsx'
import EmergencyDescription from './components/EmergencyDescription.jsx'
import LocationInput from './components/LocationInput.jsx'
import PeopleInputs from './components/PeopleInputs.jsx'
import ReportPreview from './components/ReportPreview.jsx'
import { buildRawReport } from './utils/reportBuilder.js'
import { validateReportInput } from './utils/validation.js'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'

const EMPTY_FORM = {
  location_text: '',
  latitude: null,
  longitude: null,
  description: '',
  affected_people: '',
  injured_people: '',
  people_trapped: null,
  medical_emergency: null,
}

function gpsErrorMessage(error) {
  if (!error) {
    return 'Location could not be captured. Please enter a location instead.'
  }

  if (error.code === 1) {
    return 'Location permission was denied. Please enter a location instead.'
  }

  if (error.code === 2) {
    return 'GPS is unavailable on this device. Please enter a location instead.'
  }

  if (error.code === 3) {
    return 'Location request timed out. Please try again or enter a location.'
  }

  return 'Location could not be captured. Please enter a location instead.'
}

async function parseBackendResponse(response) {
  const contentType =
    response.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    return response.json()
  }

  const text = await response.text()

  return {
    status: response.ok ? 'success' : 'error',
    detail: text || 'Backend returned an empty response.',
  }
}

export default function App() {
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState({})
  const [gpsError, setGpsError] = useState('')
  const [gpsStatus, setGpsStatus] = useState('idle')
  const [rawReport, setRawReport] = useState(null)

  function updateField(name, value) {
    setForm((current) => ({
      ...current,
      [name]: value,
    }))
  }

  function requestCurrentLocation() {
    setGpsError('')
    setGpsStatus('requesting')

    if (!navigator.geolocation) {
      setGpsStatus('idle')
      setGpsError(
        'Geolocation is not supported in this browser. Please enter a location instead.'
      )
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((current) => ({
          ...current,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }))

        setGpsStatus('idle')
        setGpsError('')

        setErrors((current) => ({
          ...current,
          location: undefined,
        }))
      },
      (error) => {
        setForm((current) => ({
          ...current,
          latitude: null,
          longitude: null,
        }))

        setGpsStatus('idle')
        setGpsError(gpsErrorMessage(error))
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    )
  }

  async function handleSubmit(event) {
    event.preventDefault()

    const result = validateReportInput(form)

    setErrors(result.errors)

    if (!result.valid) {
      return
    }

    const report = buildRawReport(
      result.parsed,
      {
        latitude: result.parsed.latitude,
        longitude: result.parsed.longitude,
      },
    )

    console.log(
      '1. Report created:',
      report,
    )

    try {
      console.log(
        '2. Sending report to RakshaSetu Module 2...',
      )

      /*
       * IMPORTANT:
       *
       * Each citizen submission is intentionally sent as
       * a single-report list.
       *
       * The backend API now retains previously submitted
       * reports and passes the accumulated report set to
       * Module 2 for duplicate clustering.
       *
       * Therefore we do NOT maintain a second report store
       * in the frontend.
       */
      const response = await fetch(
        `${API_BASE}/dashboard/module2/submit`,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json',
          },

          body: JSON.stringify([
            report,
          ]),
        },
      )

      console.log(
        '3. Backend response status:',
        response.status,
      )

      const data =
        await parseBackendResponse(response)

      console.log(
        '4. RakshaSetu pipeline response:',
        data,
      )

      if (
        !response.ok ||
        data.status !== 'success'
      ) {
        throw new Error(
          data.detail ||
          data.message ||
          'Failed to process report',
        )
      }

      console.log(
        '5. Report successfully processed!',
      )

      console.log(
        'Module 2 incident candidates:',
        data.incident_candidates,
      )

      console.log(
        'Module 3 prioritized incidents:',
        data.prioritized_incidents,
      )

      console.log(
        'Orchestration results:',
        data.results,
      )

      /*
       * Useful duplicate-clustering information for
       * development/demo debugging.
       */
      if (
        Array.isArray(
          data.incident_candidates,
        )
      ) {
        data.incident_candidates.forEach(
          (candidate) => {
            console.log(
              'Module 2 source reports for candidate:',
              candidate.source_report_ids,
            )
          },
        )
      }

      /*
       * Keep the original citizen report in the preview.
       *
       * The backend response contains the complete
       * Module 2 -> Module 3 -> Orchestrator result.
       */
      setRawReport(report)

    } catch (error) {
      console.error(
        'Report submission failed:',
        error,
      )

      alert(
        error?.message ||
        'Unable to submit the report. Please make sure the RakshaSetu backend is running.',
      )
    }
  }

  function handleNewReport() {
    setForm({
      ...EMPTY_FORM,
    })

    setErrors({})
    setGpsError('')
    setGpsStatus('idle')
    setRawReport(null)
  }

  return (
    <div className="min-h-svh bg-stone-100 text-slate-900">
      <header className="bg-red-900 px-4 py-8 text-white">
        <div className="mx-auto max-w-xl text-center">
          <div className="brand">
            <img
              src="/rakshasetu-wordmark.png"
              alt="RakshaSetu"
              className="brand-wordmark"
            />
          </div>

          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Report Emergency
          </h1>

          <p className="mt-2 text-sm text-red-100 sm:text-base">
            Report an emergency quickly so assistance can begin. This form only collects the report.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-xl px-4 py-6 sm:py-8">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          {rawReport ? (
            <ReportPreview
              rawReport={rawReport}
              onNewReport={handleNewReport}
            />
          ) : (
            <form
              className="space-y-8"
              onSubmit={handleSubmit}
              noValidate
            >
              <LocationInput
                locationText={
                  form.location_text
                }
                latitude={form.latitude}
                longitude={form.longitude}
                locationError={
                  errors.location
                }
                gpsError={gpsError}
                gpsStatus={gpsStatus}
                onLocationTextChange={(
                  value,
                ) =>
                  updateField(
                    'location_text',
                    value,
                  )
                }
                onUseCurrentLocation={
                  requestCurrentLocation
                }
              />

              <EmergencyDescription
                value={form.description}
                error={errors.description}
                onChange={(value) =>
                  updateField(
                    'description',
                    value,
                  )
                }
              />

              <PeopleInputs
                affectedPeople={
                  form.affected_people
                }
                injuredPeople={
                  form.injured_people
                }
                affectedError={
                  errors.affected_people
                }
                injuredError={
                  errors.injured_people
                }
                onAffectedChange={(
                  value,
                ) =>
                  updateField(
                    'affected_people',
                    value,
                  )
                }
                onInjuredChange={(
                  value,
                ) =>
                  updateField(
                    'injured_people',
                    value,
                  )
                }
              />

              <BooleanSelector
                id="people_trapped"
                label="Are people trapped?"
                value={
                  form.people_trapped
                }
                onChange={(value) =>
                  updateField(
                    'people_trapped',
                    value,
                  )
                }
              />

              <BooleanSelector
                id="medical_emergency"
                label="Medical emergency?"
                value={
                  form.medical_emergency
                }
                onChange={(value) =>
                  updateField(
                    'medical_emergency',
                    value,
                  )
                }
              />

              <button
                type="submit"
                className="w-full rounded-lg bg-red-800 px-4 py-4 text-base font-bold tracking-wide text-white shadow-sm hover:bg-red-900 focus:outline-none focus:ring-2 focus:ring-red-700 focus:ring-offset-2"
              >
                SUBMIT REPORT
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  )
}