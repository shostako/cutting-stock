import type { DemandRow, SolveResponse, ValidateResponse } from './types'

// /solve /validate は常に HTTP200 で返るため、フロントは本文の status / feasible で分岐する。

export interface SolveInput {
  length: number
  kerf: number
  demand: DemandRow[]
  maxExtra: number
  timeLimit?: number | null
}

function buildPayload(inp: SolveInput) {
  return {
    stock: { length: inp.length, kerf: inp.kerf },
    demand: inp.demand.map((d) => ({ length: d.length, qty: d.qty, label: d.label })),
    options: { mode: 'pareto', max_extra_bars: inp.maxExtra, time_limit_sec: inp.timeLimit ?? null },
  }
}

export async function solve(inp: SolveInput, signal?: AbortSignal): Promise<SolveResponse> {
  const r = await fetch('/solve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildPayload(inp)),
    signal,
  })
  return (await r.json()) as SolveResponse
}

export async function validate(inp: SolveInput, signal?: AbortSignal): Promise<ValidateResponse> {
  const r = await fetch('/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildPayload(inp)),
    signal,
  })
  return (await r.json()) as ValidateResponse
}

export async function health(): Promise<boolean> {
  try {
    const r = await fetch('/healthz')
    const j = await r.json()
    return Boolean(j.ok)
  } catch {
    return false
  }
}
