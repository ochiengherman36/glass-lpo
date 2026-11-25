import type { CellValue, PanelRow } from '../types'

const HIDDEN_COLUMNS = new Set(['LPO No'])
const AREA_COLUMN = 'Area (m²)'
const CONFIDENCE_COLUMN = 'Confidence'
const NEEDS_CHECK_COLUMN = 'Needs check (Y/N)'

const CONFIDENCE_STYLES: Record<string, string> = {
  High: 'bg-emerald-100 text-emerald-800',
  Medium: 'bg-amber-100 text-amber-800',
  Low: 'bg-red-100 text-red-800',
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
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${className}`}>{text}</span>
}

function Cell({ column, value }: { column: string; value: CellValue }) {
  if (column === CONFIDENCE_COLUMN && typeof value === 'string') {
    return <Badge text={value} className={CONFIDENCE_STYLES[value] ?? 'bg-slate-100 text-slate-700'} />
  }
  if (column === NEEDS_CHECK_COLUMN) {
    return value === 'Y' ? (
      <Badge text="Check" className="bg-amber-100 text-amber-800" />
    ) : (
      <Badge text="OK" className="bg-emerald-100 text-emerald-800" />
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
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
          <tr>
            {visible.map((column) => (
              <th key={column} scope="col" className="whitespace-nowrap px-3 py-2 font-semibold">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {panels.map((row) => (
            <tr key={String(row['Line'])} className="align-top">
              {visible.map((column) => {
                const value = row[column] ?? null
                const check = isCheck(value)
                return (
                  <td
                    key={column}
                    data-check={check || undefined}
                    className={`px-3 py-2 ${check ? 'bg-amber-100 font-semibold text-amber-900' : 'text-slate-800'}`}
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
