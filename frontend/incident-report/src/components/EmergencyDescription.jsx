export default function EmergencyDescription({ value, error, onChange }) {
  return (
    <section className="space-y-3" aria-labelledby="description-heading">
      <div>
        <label htmlFor="description" id="description-heading" className="block text-sm font-semibold text-slate-800">
          Describe what is happening
        </label>
        <p className="mt-1 text-sm text-slate-600">
          Share what you see. Do not worry about classifying the emergency.
        </p>
      </div>

      <textarea
        id="description"
        name="description"
        rows={6}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Water has entered several houses. Around 30 people are trapped and two people are injured."
        aria-invalid={Boolean(error)}
        aria-describedby={error ? 'description-error' : undefined}
        className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-3 text-base text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700/30"
      />

      {error && (
        <p id="description-error" className="text-sm font-medium text-red-700" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
