// labels.ts のロジック回帰: bijective base-26 採番とスキーム別ラベル解決。
import { describe, expect, it } from 'vitest'
import type { DemandRow } from './api/types'
import { alphaLabel, resolveLabels } from './labels'

const demand: DemandRow[] = [
  { length: 300, qty: 2, label: 'x' },
  { length: 500, qty: 4, label: 'y' },
  { length: 300, qty: 1, label: 'z' },
]

describe('alphaLabel', () => {
  it('表計算の列名と同じ bijective base-26', () => {
    expect(alphaLabel(0)).toBe('A')
    expect(alphaLabel(25)).toBe('Z')
    expect(alphaLabel(26)).toBe('AA')
    expect(alphaLabel(27)).toBe('AB')
    expect(alphaLabel(51)).toBe('AZ')
    expect(alphaLabel(52)).toBe('BA')
    expect(alphaLabel(701)).toBe('ZZ')
    expect(alphaLabel(702)).toBe('AAA')
  })
})

describe('resolveLabels', () => {
  it('length: 長さ文字列そのまま', () => {
    expect(resolveLabels(demand, 'length')).toEqual(['300', '500', '300'])
  })

  it('manual: 入力ラベルそのまま', () => {
    expect(resolveLabels(demand, 'manual')).toEqual(['x', 'y', 'z'])
  })

  it('alpha: 長さ降順で採番（最長=A）・同一長は同ラベル', () => {
    expect(resolveLabels(demand, 'alpha')).toEqual(['B', 'A', 'B'])
  })

  it('number: 長さ降順で採番（最長=1）', () => {
    expect(resolveLabels(demand, 'number')).toEqual(['2', '1', '2'])
  })
})
