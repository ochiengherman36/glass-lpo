import { useState } from 'react'
import { processDrawing } from './api'
import { Results } from './components/Results'
import { UploadForm } from './components/UploadForm'
import type { ProcessResult } from './types'

function App() {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ProcessResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(file: File) {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await processDrawing(file))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Glass Drawing to LPO</h1>
        <p className="mt-1 text-sm text-slate-600">
          Upload a phone photo of a glass drawing. The photo is cleaned up, every panel is read, and anything unclear is
          marked CHECK instead of guessed.
        </p>
      </header>

      <UploadForm busy={busy} onSubmit={handleSubmit} />

      {busy && (
        <div role="progressbar" aria-label="Processing drawing" className="flex items-center gap-3 text-sm text-slate-600">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
          Enhancing the photo and reading the drawing. This usually takes under a minute.
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && <Results result={result} />}
    </main>
  )
}

export default App
