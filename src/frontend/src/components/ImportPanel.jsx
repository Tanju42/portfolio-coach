import React, { useEffect, useState } from 'react'
import { fetchImportHelp, uploadCsv } from '../api.js'

export default function ImportPanel({ onImported }) {
  const [help, setHelp] = useState(null)
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchImportHelp().then(setHelp).catch((err) => setError(err.message))
  }, [])

  async function submit(event) {
    event.preventDefault()
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      setResult(await uploadCsv(file))
      setFile(null)
      onImported?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>Import your Binance transaction history</h2>
      <p className="lead">
        The coach needs your trade history to calculate cost basis and profit/loss.
        Export a CSV from Binance and upload it here — everything is processed locally.
      </p>
      {help && (
        <ol className="help-steps">
          {help.steps.map((step, index) => (
            <li key={index}>{step}</li>
          ))}
        </ol>
      )}
      {help && (
        <p className="note">
          Expected columns: {help.expected_columns.join(', ')}.
        </p>
      )}
      <form className="upload" onSubmit={submit}>
        <input
          type="file"
          accept=".csv"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
        <button type="submit" disabled={!file || busy}>
          {busy ? 'Importing…' : 'Import CSV'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="import-result">
          <h3>Imported ✓</h3>
          <ul>
            <li>{result.summary.rows_total} rows processed</li>
            <li>{result.summary.trades} trades matched</li>
            <li>{result.summary.income_events} income events (rewards, interest, airdrops)</li>
            <li>{result.summary.earn_moves} earn moves (no cost impact)</li>
            <li>
              Unknown-basis cash: ${result.summary.cash_spent_unknown_target_usd}
            </li>
          </ul>
          {result.summary.warnings.map((warning, index) => (
            <p key={index} className="note">{warning}</p>
          ))}
        </div>
      )}
    </section>
  )
}
