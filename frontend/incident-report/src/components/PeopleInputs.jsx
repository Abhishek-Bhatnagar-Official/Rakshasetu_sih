export default function PeopleInputs({
  affectedPeople,
  injuredPeople,
  affectedError,
  injuredError,
  onAffectedChange,
  onInjuredChange,
}) {
  return (
    <section className="grid gap-4 sm:grid-cols-2">
      <div className="space-y-2">
        <label htmlFor="affected_people" className="block text-sm font-semibold text-slate-800">
          Approx. affected people
        </label>
        <input
          id="affected_people"
          name="affected_people"
          type="number"
          inputMode="numeric"
          min="0"
          step="1"
          value={affectedPeople}
          onChange={(event) => onAffectedChange(event.target.value)}
          placeholder="30"
          aria-invalid={Boolean(affectedError)}
          aria-describedby={affectedError ? 'affected-error' : undefined}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-base text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700/30"
        />
        {affectedError && (
          <p id="affected-error" className="text-sm font-medium text-red-700" role="alert">
            {affectedError}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="injured_people" className="block text-sm font-semibold text-slate-800">
          Approx. injured people
        </label>
        <input
          id="injured_people"
          name="injured_people"
          type="number"
          inputMode="numeric"
          min="0"
          step="1"
          value={injuredPeople}
          onChange={(event) => onInjuredChange(event.target.value)}
          placeholder="2"
          aria-invalid={Boolean(injuredError)}
          aria-describedby={injuredError ? 'injured-error' : undefined}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-base text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700/30"
        />
        {injuredError && (
          <p id="injured-error" className="text-sm font-medium text-red-700" role="alert">
            {injuredError}
          </p>
        )}
      </div>
    </section>
  )
}
