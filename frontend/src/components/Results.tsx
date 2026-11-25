import type { ProcessResult } from '../types'
import { PanelTable } from './PanelTable'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_3px_rgba(16,24,40,0.07)]">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-1.5 text-2xl font-bold tabular-nums tracking-tight text-slate-900">{value}</div>
    </div>
  )
}

function Photo({ title, src }: { title: string; src: string }) {
  return (
    <figure className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_3px_rgba(16,24,40,0.07)]">
      <figcaption className="border-b border-slate-100 bg-slate-50/60 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </figcaption>
      <img src={src} alt={title} className="max-h-[480px] w-full bg-slate-50 object-contain" />
    </figure>
  )
}

export function Results({ result }: { result: ProcessResult }) {
  const { totals, flags, urls } = result
  const area = `${totals.area_m2.toFixed(3)} m²${totals.area_complete ? '' : ' *'}`

  return (
    <section className="flex flex-col gap-7">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-mono text-xl font-bold tracking-tight text-teal-800">{result.lpo_no}</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {result.source_name} · {formatDate(result.issued_at)}
          </p>
        </div>
        <div className="flex gap-3">
          <a
            href={urls.xlsx}
            download
            className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-500 active:bg-emerald-700"
          >
            Download Excel
          </a>
          <a
            href={urls.pdf}
            download
            className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-700 active:bg-slate-950"
          >
            Download PDF LPO
          </a>
        </div>
      </div>

      <div
        role="status"
        className={`rounded-xl border-l-4 px-4 py-3.5 text-sm font-semibold shadow-sm ${
          result.needs_check
            ? 'border-amber-400 bg-amber-50 text-amber-900'
            : 'border-emerald-500 bg-emerald-50 text-emerald-900'
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
      {!totals.area_complete && <p className="-mt-4 text-xs text-slate-400">* Excludes lines whose size is marked CHECK.</p>}

      <PanelTable columns={result.columns} panels={result.panels} />

      {flags.length > 0 && (
        <div className="rounded-2xl border-l-4 border-red-400 bg-red-50 p-5 shadow-sm">
          <h3 className="text-base font-bold text-red-800">Needs human check ({flags.length})</h3>
          <ul className="mt-2.5 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-red-900">
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

      <details className="rounded-xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-slate-400 transition-colors hover:text-teal-700">
          Processing details
        </summary>
        <ul className="mt-2.5 list-disc space-y-1 pl-5">
          {result.steps_applied.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
        <p className="mt-2.5 border-t border-slate-100 pt-2.5 text-xs text-slate-400">
          Model {result.usage.model}: {result.usage.input_tokens} input / {result.usage.output_tokens} output tokens
          {result.usage.fallback_used ? ' (served by fallback model)' : ''}
        </p>
      </details>
    </section>
  )
}