import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { ProcessResult } from './types'

const COLUMNS = [
  'LPO No', 'Line', 'Panel ID', 'Width (mm)', 'Height (mm)', 'Qty', 'Thickness (mm)', 'Glass type', 'Area (m²)',
  'Hole count', 'Hole diameters (mm)', 'Hole positions', 'Notches/offcuts', 'Grooves/edge work', 'Notes',
  'Confidence', 'Needs check (Y/N)',
]

function row(line: number, panelId: string, width: number | string, area: number | string, check: 'Y' | 'N') {
  return {
    'LPO No': 'LPO-20261125-143005', Line: line, 'Panel ID': panelId, 'Width (mm)': width, 'Height (mm)': 1000,
    Qty: 1, 'Thickness (mm)': 6, 'Glass type': 'clear', 'Area (m²)': area, 'Hole count': 1,
    'Hole diameters (mm)': '25', 'Hole positions': 'not dimensioned', 'Notches/offcuts': '',
    'Grooves/edge work': '', Notes: '', Confidence: check === 'Y' ? 'Low' : 'High', 'Needs check (Y/N)': check,
  }
}

const RESULT: ProcessResult = {
  job_id: 'job-1',
  lpo_no: 'LPO-20261125-143005',
  issued_at: '2026-11-25T14:30:05',
  source_name: 'hard.jpeg',
  needs_check: true,
  steps_applied: ['removed shadows and uneven lighting, boosted contrast (CLAHE)'],
  columns: COLUMNS,
  panels: [row(1, 'P1', 900, 0.9, 'N'), row(2, 'P2', 'CHECK (600?)', 'CHECK', 'Y')],
  flags: [{ panel_id: 'P2', field: 'width', message: "P2: width unclear (raw: '650 crossed out, 600 written')", severity: 'critical' }],
  totals: { lines: 2, pieces: 2, area_m2: 0.9, area_complete: false, holes: 2 },
  usage: { model: 'claude-opus-5-5', input_tokens: 4100, output_tokens: 2300, fallback_used: false },
  urls: {
    original: '/outputs/job-1/original.jpg',
    enhanced: '/outputs/job-1/enhanced.jpg',
    xlsx: '/outputs/job-1/LPO-20261125-143005.xlsx',
    pdf: '/outputs/job-1/LPO-20261125-143005.pdf',
    json: '/outputs/job-1/result.json',
  },
}

const fetchMock = vi.fn()

function respondWith(status: number, body: unknown) {
  fetchMock.mockResolvedValueOnce({ ok: status >= 200 && status < 300, status, json: async () => body })
}

async function uploadDrawing() {
  const user = userEvent.setup()
  const file = new File(['fake image'], 'hard.jpeg', { type: 'image/jpeg' })
  await user.upload(screen.getByLabelText(/drawing photo/i), file)
  await user.click(screen.getByRole('button', { name: /process drawing/i }))
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  fetchMock.mockReset()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders the upload control with the button disabled until a file is chosen', () => {
    render(<App />)

    expect(screen.getByLabelText(/drawing photo/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /process drawing/i })).toBeDisabled()
  })

  it('posts the file and renders panels, CHECK cells, flags and downloads', async () => {
    respondWith(200, RESULT)
    render(<App />)

    await uploadDrawing()

    expect(await screen.findByRole('heading', { name: 'LPO-20261125-143005' })).toBeInTheDocument()
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/process')
    expect((options.body as FormData).get('file')).toBeInstanceOf(File)

    const table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByText('CHECK (600?)').closest('td')).toHaveAttribute('data-check', 'true')
    expect(within(table).getByText('900').closest('td')).not.toHaveAttribute('data-check')
    expect(within(table).getByText('0.900')).toBeInTheDocument()
    expect(within(table).getByText('Low')).toBeInTheDocument()

    expect(screen.getByText("P2: width unclear (raw: '650 crossed out, 600 written')")).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('1 item needs a human check before cutting.')
    expect(screen.getByRole('link', { name: /download excel/i })).toHaveAttribute('href', RESULT.urls.xlsx)
    expect(screen.getByRole('link', { name: /download pdf/i })).toHaveAttribute('href', RESULT.urls.pdf)
    expect(screen.getByRole('img', { name: 'Enhanced' })).toHaveAttribute('src', RESULT.urls.enhanced)
  })

  it('shows the server error message when processing fails', async () => {
    respondWith(502, { detail: 'Anthropic API rate limit reached. Wait a minute and try again.' })
    render(<App />)

    await uploadDrawing()

    expect(await screen.findByRole('alert')).toHaveTextContent('Anthropic API rate limit reached. Wait a minute and try again.')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows a clear message when the server cannot be reached', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    render(<App />)

    await uploadDrawing()

    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the server. Is the backend running?')
  })
})
