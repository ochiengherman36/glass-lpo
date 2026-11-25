import type { ProcessResult } from './types'

export const PROCESS_URL = '/api/process'

export async function processDrawing(file: File): Promise<ProcessResult> {
  const body = new FormData()
  body.append('file', file)

  let response: Response
  try {
    response = await fetch(PROCESS_URL, { method: 'POST', body })
  } catch {
    throw new Error('Could not reach the server. Is the backend running?')
  }

  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return (await response.json()) as ProcessResult
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json()
    if (data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string') {
      return data.detail
    }
  } catch {
    return `Request failed (${response.status})`
  }
  return `Request failed (${response.status})`
}
