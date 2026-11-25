export type CellValue = string | number | null

export type PanelRow = Record<string, CellValue>

export type Severity = 'critical' | 'minor'

export interface Flag {
  panel_id: string | null
  field: string
  message: string
  severity: Severity
}

export interface Totals {
  lines: number
  pieces: number
  area_m2: number
  area_complete: boolean
  holes: number
}

export interface Usage {
  model: string
  input_tokens: number
  output_tokens: number
  fallback_used: boolean
}

export interface ResultUrls {
  original: string
  enhanced: string
  xlsx: string
  pdf: string
  json: string
}

export interface ProcessResult {
  job_id: string
  lpo_no: string
  issued_at: string
  source_name: string
  needs_check: boolean
  steps_applied: string[]
  columns: string[]
  panels: PanelRow[]
  flags: Flag[]
  totals: Totals
  usage: Usage
  urls: ResultUrls
}
