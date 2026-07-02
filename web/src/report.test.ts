// report.ts のロジック回帰: 生産突合（過剰生産ゼロの約束のフロント側検算）と CSV 生成。
import { describe, expect, it } from 'vitest'
import type { DemandRow, Solution } from './api/types'
import { buildPlanCsv, computeProduction } from './report'

const solution: Solution = {
  bars_used: 3,
  total_waste: 100,
  waste_ratio: 0.0278,
  num_pattern_types: 2,
  optimality: {
    status: 'Optimal',
    mip_gap: 0,
    lp_lower_bound: 3,
    proven_optimal: true,
    patterns_min_proven: true,
    timed_out: false,
  },
  patterns: [
    {
      cuts: [500, 500, 200],
      item_counts: { '500': 2, '200': 1 },
      stock_length: 1200,
      waste: 0,
      run_count: 2,
      segments: [],
    },
    {
      cuts: [500, 200, 200, 200],
      item_counts: { '500': 1, '200': 3 },
      stock_length: 1200,
      waste: 100,
      run_count: 1,
      segments: [],
    },
  ],
}

const demand: DemandRow[] = [
  { length: 500, qty: 5, label: 'A' },
  { length: 200, qty: 5, label: 'B' },
]

describe('computeProduction', () => {
  it('パターン×本数から品目別生産を集計し需要と突合する', () => {
    const rows = computeProduction(demand, solution)
    expect(rows).toEqual([
      { length: 500, label: 'A', demand: 5, produced: 5, over: 0 },
      { length: 200, label: 'B', demand: 5, produced: 5, over: 0 },
    ])
  })

  it('需要ちょうど（== 制約）なら全行 over=0', () => {
    // ソルバは 2026-07-02 以降、需要 == で解く。この約束が破れたら over>0 が現れ GUI が警告する。
    const rows = computeProduction(demand, solution)
    expect(rows.every((r) => r.over === 0)).toBe(true)
  })

  it('過剰生産があれば over に正しく現れる（安全網の検算）', () => {
    const less: DemandRow[] = [
      { length: 500, qty: 4, label: 'A' },
      { length: 200, qty: 5, label: 'B' },
    ]
    const rows = computeProduction(less, solution)
    expect(rows[0]).toMatchObject({ length: 500, demand: 4, produced: 5, over: 1 })
  })

  it('同一長さの需要行は合算される（ソルバのマージと整合）', () => {
    const split: DemandRow[] = [
      { length: 500, qty: 3, label: 'A' },
      { length: 500, qty: 2, label: 'A2' },
      { length: 200, qty: 5, label: 'B' },
    ]
    const rows = computeProduction(split, solution)
    expect(rows[0]).toMatchObject({ length: 500, demand: 5, produced: 5, over: 0 })
  })

  it('長さ降順に整列される', () => {
    const rows = computeProduction(demand, solution)
    expect(rows.map((r) => r.length)).toEqual([500, 200])
  })
})

describe('buildPlanCsv', () => {
  const csv = buildPlanCsv({
    length: 1200,
    kerf: 5,
    solution,
    production: computeProduction(demand, solution),
  })
  const lines = csv.split('\r\n')

  it('サマリ・パターン表・品目表を含む', () => {
    expect(lines[0]).toBe('カット指示書')
    expect(csv).toContain('原材料長,1200,mm')
    expect(csv).toContain('カット代,5,mm')
    expect(csv).toContain('必要原材料,3,本')
    expect(csv).toContain('切り方,内容(mm),本数,残材(mm)')
    expect(csv).toContain('1,500 + 500 + 200,2,0')
    expect(csv).toContain('品目,長さ(mm),需要,生産,過剰')
    expect(csv).toContain('A,500,5,5,0')
  })

  it('カンマ・引用符・改行を含むセルは RFC4180 エスケープされる', () => {
    const tricky = buildPlanCsv({
      length: 1200,
      kerf: 5,
      solution,
      production: [{ length: 500, label: 'A,"B"', demand: 1, produced: 1, over: 0 }],
    })
    expect(tricky).toContain('"A,""B""",500,1,1,0')
  })

  it('行区切りは CRLF（Excel 互換）', () => {
    expect(csv.includes('\r\n')).toBe(true)
    expect(csv.split('\r\n').length).toBeGreaterThan(10)
  })
})
