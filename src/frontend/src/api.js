const API = '/api'

async function jsonOrThrow(response) {
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText)
    throw new Error(detail || `request failed (${response.status})`)
  }
  return response.json()
}

export function fetchHealth() {
  return fetch(`${API}/health`).then(jsonOrThrow)
}

export function fetchPortfolio() {
  return fetch(`${API}/portfolio`).then(jsonOrThrow)
}

export function fetchSignals() {
  return fetch(`${API}/signals`).then(jsonOrThrow)
}

export function fetchImportHelp() {
  return fetch(`${API}/import/help`).then(jsonOrThrow)
}

export function sendChat(message, sessionId, beginnerMode) {
  return fetch(`${API}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, beginner_mode: beginnerMode }),
  }).then(jsonOrThrow)
}

export function uploadCsv(file) {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${API}/import/csv`, { method: 'POST', body: form }).then(jsonOrThrow)
}
