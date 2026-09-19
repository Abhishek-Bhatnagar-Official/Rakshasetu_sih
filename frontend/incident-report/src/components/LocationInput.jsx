export default function LocationInput({
  locationText,
  latitude,
  longitude,
  locationError,
  gpsError,
  gpsStatus,
  onLocationTextChange,
  onUseCurrentLocation,
}) {
  const hasCoordinates =
    typeof latitude === 'number' && typeof longitude === 'number'

  return (
    <section className="space-y-3" aria-labelledby="location-heading">
      <div>
        <label htmlFor="location_text" id="location-heading" className="block text-sm font-semibold text-slate-800">
          Location
        </label>
        <p className="mt-1 text-sm text-slate-600">
          Enter a place name, or use your device location. Coordinates are captured automatically.
        </p>
      </div>

      <input
        id="location_text"
        name="location_text"
        type="text"
        autoComplete="street-address"
        value={locationText}
        onChange={(event) => onLocationTextChange(event.target.value)}
        placeholder="Raj Nagar Extension, Ghaziabad"
        aria-invalid={Boolean(locationError)}
        aria-describedby={locationError ? 'location-error' : undefined}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-base text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-700/30"
      />

      <button
        type="button"
        onClick={onUseCurrentLocation}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-red-800 bg-white px-4 py-3 text-base font-semibold text-red-800 shadow-sm hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-700/40 sm:w-auto"
      >
        <span aria-hidden="true">📍</span>
        Use My Current Location
      </button>

      {gpsStatus === 'requesting' && (
        <p className="text-sm text-slate-600" role="status">
          Requesting location permission…
        </p>
      )}

      {hasCoordinates && (
        <div
          className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-800"
          aria-live="polite"
        >
          <p className="font-semibold">Current location</p>
          <p className="mt-1 font-mono">Latitude: {latitude}</p>
          <p className="font-mono">Longitude: {longitude}</p>
        </div>
      )}

      {gpsError && (
        <p className="text-sm font-medium text-red-700" role="alert">
          {gpsError}
        </p>
      )}

      {locationError && (
        <p id="location-error" className="text-sm font-medium text-red-700" role="alert">
          {locationError}
        </p>
      )}
    </section>
  )
}
