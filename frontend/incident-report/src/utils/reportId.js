const STORAGE_KEY = 'rakshasetu_report_seq'

function readStoredSequence() {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY)
    const parsed = Number.parseInt(raw ?? '', 10)
    return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0
  } catch {
    return 0
  }
}

function writeStoredSequence(value) {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, String(value))
  } catch {
    // Ignore storage failures in restricted environments.
  }
}

let sequence = readStoredSequence()

export function generateReportId() {
  sequence += 1
  writeStoredSequence(sequence)
  return `R${String(sequence).padStart(3, '0')}`
}

export function resetReportIdSequence(value = 0) {
  sequence = value
  writeStoredSequence(sequence)
}
