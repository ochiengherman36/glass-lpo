import type { CellValue, PanelRow } from '../types'

const HIDDEN_COLUMNS = new Set(['LPO No'])
const AREA_COLUMN = 'Area (m²)'
const CONFIDENCE_COLUMN = 'Confidence'
const NEEDS_CHECK_COLUMN = 'Needs check (Y/N)'

const CONFIDENCE_STYLES: Record<string, string> = {
  High: 'bg-emerald-50 text-emerald-700 ring-emerald-600/30',
  Medium: 'bg-amber-50 text-amber-700 ring-amber-600/30',
  Low: 'bg-red-50 text-red-700 ring-red-600/30',
}

function isCheck(value: CellValue): boolean {
  return typeof value === 'string' && value.startsWith('CHECK')
}

function formatCell(column: string, value: CellValue): string {
  if (value === null) return ''
  if (column === AREA_COLUMN && typeof value === 'number') return value.toFixed(3)
  return String(value)
}

function Badge({ text, className }: { text: string; className: string }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${className}`}>
      {text}
    </span>
  )
}

function Cell({ column, value }: { column: string; value: CellValue }) {
  if (column === CONFIDENCE_COLUMN && typeof value === 'string') {
    return <Badge text={value} className={CONFIDENCE_STYLES[value] ?? 'bg-slate-100 text-slate-600 ring-slate-500/20'} />
  }
  if (column === NEEDS_CHECK_COLUMN) {
    return value === 'Y' ? (
      <Badge text="Check" className="bg-amber-50 text-amber-700 ring-amber-600/30" />
    ) : (
      <Badge text="OK" className="bg-emerald-50 text-emerald-700 ring-emerald-600/30" />
    )
  }
  return <>{formatCell(column, value)}</>
}

interface PanelTableProps {
  columns: string[]
  panels: PanelRow[]
}

export function PanelTable({ columns, panels }: PanelTableProps) {
  const visible = columns.filter((column) => !HIDDEN_COLUMNS.has(column))

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_3px_rgba(16,24,40,0.07)]">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50/80 text-[11px] uppercase tracking-wider text-slate-500">
          <tr>
            {visible.map((column) => (
              <th key={column} scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {panels.map((row) => (
            <tr key={String(row['Line'])} className="align-top transition-colors hover:bg-teal-50/40">
              {visible.map((column) => {
                const value = row[column] ?? null
                const check = isCheck(value)
                return (
                  <td
                    key={column}
                    data-check={check || undefined}
                    className={`px-4 py-3 tabular-nums ${
                      check ? 'bg-amber-50 font-semibold text-amber-900' : 'text-slate-700'
                    }`}
                  >
                    <Cell column={column} value={value} />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}