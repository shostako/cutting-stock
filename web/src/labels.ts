import type { DemandRow } from './api/types'

// ラベル付与スキーム。length=長さそのまま / alpha=A,B,C… / number=1,2,3… / manual=任意入力。
export type LabelScheme = 'length' | 'alpha' | 'number' | 'manual'

export const LABEL_SCHEMES: { key: LabelScheme; label: string }[] = [
  { key: 'length', label: '長さ' },
  { key: 'alpha', label: 'A,B,C' },
  { key: 'number', label: '1,2,3' },
  { key: 'manual', label: '手動' },
]

// 0→A, 25→Z, 26→AA, 27→AB …（表計算の列名と同じ bijective base-26）
export function alphaLabel(n: number): string {
  let s = ''
  let k = n + 1
  while (k > 0) {
    const r = (k - 1) % 26
    s = String.fromCharCode(65 + r) + s
    k = Math.floor((k - 1) / 26)
  }
  return s
}

// 各需要行のラベルを解決する。alpha/number は「長さ降順」で採番（最長 = A / 1）し、
// 凡例（長さ降順ソート）と並びを一致させる。同一長は同じラベルになる。
export function resolveLabels(demand: DemandRow[], scheme: LabelScheme): string[] {
  if (scheme === 'manual') return demand.map((d) => d.label)
  if (scheme === 'length') return demand.map((d) => String(d.length))
  const distinctDesc = Array.from(new Set(demand.map((d) => d.length))).sort((a, b) => b - a)
  const rank = new Map<number, number>()
  distinctDesc.forEach((len, i) => rank.set(len, i))
  return demand.map((d) => {
    const i = rank.get(d.length) ?? 0
    return scheme === 'alpha' ? alphaLabel(i) : String(i + 1)
  })
}
