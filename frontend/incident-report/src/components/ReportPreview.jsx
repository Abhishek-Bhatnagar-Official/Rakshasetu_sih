const SUMMARY_FIELDS = [
  ['Report ID', 'report_id'],
  ['Submission time', 'submitted_at'],
  ['Source', 'source_type'],
  ['Location', 'location_text'],
  ['Latitude', 'latitude'],
  ['Longitude', 'longitude'],
  ['Description', 'description'],
  ['Affected people', 'affected_people'],
  ['Injured people', 'injured_people'],
  ['People trapped', 'people_trapped'],
  ['Medical emergency', 'medical_emergency'],
]

function displayValue(value) {
  if (value === null) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

export default function ReportPreview({ rawReport, onNewReport }) {
  return (
    <section className="space-y-6" aria-labelledby="success-heading">
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-4">
        <h2 id="success-heading" className="text-xl font-bold text-emerald-900">
          Report submitted successfully
        </h2>
        <p className="mt-1 text-sm text-emerald-800">
          This is a local preview for testing. The report is not sent anywhere.
        </p>
      </div>

      <dl className="grid gap-3 sm:grid-cols-2">
        {SUMMARY_FIELDS.map(([label, key]) => (
          <div key={key} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
            <dd className="mt-1 break-words text-sm text-slate-900">{displayValue(rawReport[key])}</dd>
          </div>
        ))}
      </dl>

      <div>
        <h3 className="text-sm font-semibold text-slate-800">Generated raw_report</h3>
        <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-950 p-4 text-left text-xs leading-relaxed text-emerald-100">
          {JSON.stringify(rawReport, null, 2)}
        </pre>
      </div>

      <button
        type="button"
        onClick={onNewReport}
        className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-base font-semibold text-slate-800 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-red-700/40"
      >
        Submit another report
      </button>
    </section>
  )
}
