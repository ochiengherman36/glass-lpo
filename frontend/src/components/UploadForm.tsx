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
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-end">
      <label className="flex flex-1 flex-col gap-2 text-sm font-medium text-slate-700">
        Drawing photo (JPG or PNG)
        <input
          type="file"
          accept="image/jpeg,image/png"
          disabled={busy}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:font-medium file:text-slate-700 hover:file:bg-slate-200"
        />
      </label>
      <button
        type="submit"
        disabled={!file || busy}
        className="rounded-md bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {busy ? 'Processing…' : 'Process drawing'}
      </button>
    </form>
  )
}
