// 現場向けレポート: 過剰生産の算出 と カット指示書CSVの生成。
// すべて API レスポンス + solved 時点の需要から計算（バックエンド非依存）。

import type { DemandRow, Solution } from './api/types'

export interface ProductionRow {
  length: number
  label: string
  demand: number
  produced: number
  over: number
}

// 品目別に「需要 vs 生産」を突き合わせる。生産はパターンの item_counts × run_count の総和。
// 需要は同一長さを合算（ソルバが長さでマージするため整合させる）。
export function computeProduction(demand: DemandRow[], solution: Solution): ProductionRow[] {
  const produced = new Map<number, number>()
  for (const p of solution.patterns) {
    for (const [lenStr, cnt] of Object.entries(p.item_counts)) {
      const len = Number(lenStr)
      produced.set(len, (produced.get(len) ?? 0) + cnt * p.run_count)
    }
  }
  const byLen = new Map<number, { qty: number; label: string }>()
  for (const d of demand) {
    const e = byLen.get(d.length)
    if (e) e.qty += d.qty
    else byLen.set(d.length, { qty: d.qty, label: d.label })
  }
  const rows: ProductionRow[] = []
  for (const [length, { qty, label }] of byLen) {
    const prod = produced.get(length) ?? 0
    rows.push({ length, label, demand: qty, produced: prod, over: Math.max(0, prod - qty) })
  }
  return rows.sort((a, b) => b.length - a.length)
}

function esc(v: string | number): string {
  const s = String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

// 選んだ解を、現場へ渡すカット指示書CSV（サマリ + パターン表 + 品目生産表）にする。
export function buildPlanCsv(args: {
  length: number
  kerf: number
  solution: Solution
  production: ProductionRow[]
}): string {
  const { length, kerf, solution, production } = args
  const rows: (string | number)[][] = [
    ['カット指示書'],
    ['原材料長', length, 'mm'],
    ['カット代', kerf, 'mm'],
    ['必要原材料', solution.bars_used, '本'],
    ['総廃棄', solution.total_waste, 'mm'],
    ['廃棄率', (solution.waste_ratio * 100).toFixed(2) + '%'],
    ['切り方の種類', solution.num_pattern_types],
    [],
    ['切り方', '内容(mm)', '本数', '残材(mm)'],
  ]
  solution.patterns.forEach((p, i) => {
    rows.push([i + 1, p.cuts.join(' + '), p.run_count, p.waste])
  })
  rows.push([], ['品目', '長さ(mm)', '需要', '生産', '過剰'])
  for (const r of production) {
    rows.push([r.label || r.length, r.length, r.demand, r.produced, r.over])
  }
  return rows.map((r) => r.map(esc).join(',')).join('\r\n')
}

// Excel(日本語)で文字化けしないよう BOM 付き UTF-8 で保存。
export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
