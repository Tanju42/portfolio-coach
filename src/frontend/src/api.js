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

export function fetchPortfolios() {
  return fetch(`${API}/portfolios`).then(jsonOrThrow)
}

export function fetchHistory(range) {
  return fetch(`${API}/portfolio/history?range=${encodeURIComponent(range)}`).then(jsonOrThrow)
}

export function fetchAssetDetail(asset) {
  return fetch(`${API}/asset/${encodeURIComponent(asset)}`).then(jsonOrThrow)
}

export function fetchAllocation() {
  return fetch(`${API}/allocation`).then(jsonOrThrow)
}

export function setAllocationTargets(targets) {
  return fetch(`${API}/allocation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ targets }),
  }).then(jsonOrThrow)
}

export function fetchRisk() {
  return fetch(`${API}/risk`).then(jsonOrThrow)
}

export function fetchWatchlist() {
  return fetch(`${API}/watchlist`).then(jsonOrThrow)
}

export function addWatch(symbol, kind) {
  return fetch(`${API}/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, kind }),
  }).then(jsonOrThrow)
}

export function removeWatch(symbol) {
  return fetch(`${API}/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }).then(jsonOrThrow)
}

export function fetchSignals() {
  return fetch(`${API}/signals`).then(jsonOrThrow)
}

export function fetchImportHelp() {
  return fetch(`${API}/import/help`).then(jsonOrThrow)
}

export function fetchMarket() {
  return fetch(`${API}/market`).then(jsonOrThrow)
}

export function fetchKnowledge() {
  return fetch(`${API}/knowledge`).then(jsonOrThrow)
}

export function researchKnowledge(topic) {
  return fetch(`${API}/knowledge/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  }).then(jsonOrThrow)
}

export function fetchSettings() {
  return fetch(`${API}/settings`).then(jsonOrThrow)
}

export function setAccountMode(mode) {
  return fetch(`${API}/settings/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  }).then(jsonOrThrow)
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
