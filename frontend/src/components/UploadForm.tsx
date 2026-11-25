import { useState, type FormEvent } from 'react'

interface UploadFormProps {
  busy: boolean
  onSubmit: (file: File) => void
}

export function UploadForm({ busy, onSubmit }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (file) onSubmit(file)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-5 rounded-2xl border border-slate-200/80 bg-white p-6 shadow-[0_1px_3px_rgba(16,24,40,0.07)] sm:flex-row sm:items-end"
    >
      <label className="flex flex-1 flex-col gap-2.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Drawing photo (JPG or PNG)
        <input
          type="file"
          accept="image/jpeg,image/png"
          disabled={busy}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full cursor-pointer rounded-xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-3 text-sm normal-case tracking-normal text-slate-600 transition-colors hover:border-teal-500 hover:bg-teal-50/50 file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-teal-700 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white file:transition-colors hover:file:bg-teal-600"
        />
      </label>
      <button
        type="submit"
        disabled={!file || busy}
        className="rounded-xl bg-teal-700 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-600 active:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
      >
        {busy ? 'Processing…' : 'Process drawing'}
      </button>
    </form>
  )
}