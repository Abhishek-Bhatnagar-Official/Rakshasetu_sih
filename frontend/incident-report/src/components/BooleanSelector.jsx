const OPTIONS = [
  { label: 'Yes', value: true },
  { label: 'No', value: false },
  { label: "Don't Know", value: null },
]

export default function BooleanSelector({ id, label, value, onChange }) {
  return (
    <fieldset className="space-y-3">
      <legend id={`${id}-legend`} className="text-sm font-semibold text-slate-800">
        {label}
      </legend>
      <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-labelledby={`${id}-legend`}>
        {OPTIONS.map((option) => {
          const selected = value === option.value
          return (
            <button
              key={option.label}
              id={option.label === "Don't Know" ? `${id}-unknown` : `${id}-${option.label.toLowerCase()}`}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(option.value)}
              className={`rounded-lg border px-3 py-3 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-red-700/40 ${
                selected
                  ? 'border-red-800 bg-red-800 text-white'
                  : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-50'
              }`}
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}
