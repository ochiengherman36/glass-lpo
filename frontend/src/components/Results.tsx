import type { ProcessResult } from '../types'
import { PanelTable } from './PanelTable'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
    </div>
  )
}

function Photo({ title, src }: { title: string; src: string }) {
  return (
    <figure className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <figcaption className="border-b border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">{title}</figcaption>
      <img src={src} alt={title} className="max-h-[480px] w-full object-contain bg-slate-50" />
    </figure>
  )
}

export function Results({ result }: { result: ProcessResult }) {
  const { totals, flags, urls } = result
  const area = `${totals.area_m2.toFixed(3)} m²${totals.area_complete ? '' : ' *'}`

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{result.lpo_no}</h2>
          <p className="text-sm text-slate-500">
            {result.source_name} · {formatDate(result.issued_at)}
          </p>
        </div>
        <div className="flex gap-3">
          <a href={urls.xlsx} download className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600">
            Download Excel
          </a>
          <a href={urls.pdf} download className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">
            Download PDF LPO
          </a>
        </div>
      </div>

      <div
        role="status"
        className={`rounded-lg border px-4 py-3 text-sm font-medium ${
          result.needs_check ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-emerald-300 bg-emerald-50 text-emerald-900'
        }`}
      >
        {result.needs_check
          ? `${flags.length} ${flags.length === 1 ? 'item needs' : 'items need'} a human check before cutting.`
          : 'All values were read clearly and passed the checks.'}
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Lines" value={String(totals.lines)} />
        <Stat label="Pieces" value={String(totals.pieces)} />
        <Stat label="Total area" value={area} />
        <Stat label="Total holes" value={String(totals.holes)} />
      </div>
      {!totals.area_complete && <p className="-mt-3 text-xs text-slate-500">* Excludes lines whose size is marked CHECK.</p>}

      <PanelTable columns={result.columns} panels={result.panels} />

      {flags.length > 0 && (
        <div className="rounded-lg border-2 border-red-300 bg-red-50 p-4">
          <h3 className="text-base font-semibold text-red-800">Needs human check ({flags.length})</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-900">
            {flags.map((flag, index) => (
              <li key={`${flag.message}-${index}`}>{flag.message}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Photo title="Original photo" src={urls.original} />
        <Photo title="Enhanced" src={urls.enhanced} />
      </div>

      <details className="text-sm text-slate-600">
        <summary className="cursor-pointer font-medium">Processing details</summary>
        <ul className="mt-2 list-disc pl-5">
          {result.steps_applied.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
        <p className="mt-2">
          Model {result.usage.model}: {result.usage.input_tokens} input / {result.usage.output_tokens} output tokens
          {result.usage.fallback_used ? ' (served by fallback model)' : ''}
        </p>
      </details>
    </section>
  )
}
