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
    <main className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
      <header className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-600 to-teal-800 text-lg font-extrabold text-white shadow-md shadow-teal-900/20">
          G
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Glass Drawing to LPO</h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-slate-500">
            Upload a phone photo of a glass drawing. The photo is cleaned up, every panel is read, and anything unclear
            is marked CHECK instead of guessed.
          </p>
        </div>
      </header>

      <UploadForm busy={busy} onSubmit={handleSubmit} />

      {busy && (
        <div
          role="progressbar"
          aria-label="Processing drawing"
          className="flex items-center gap-3 rounded-xl border border-teal-100 bg-teal-50/60 px-4 py-3 text-sm font-medium text-teal-900"
        >
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-teal-200 border-t-teal-700" />
          Enhancing the photo and reading the drawing. This usually takes under a minute.
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800 shadow-sm">
          {error}
        </div>
      )}

      {result && <Results result={result} />}
    </main>
  )
}

export default App