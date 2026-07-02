// colors.ts のロジック回帰: 長さ→色の安定割当。
import { describe, expect, it } from 'vitest'
import { makeColorOf } from './colors'

describe('makeColorOf', () => {
  it('同じ長さには常に同じ色（重複・順序に依らず安定）', () => {
    const a = makeColorOf([500, 200, 500, 340])
    const b = makeColorOf([340, 500, 200])
    for (const len of [200, 340, 500]) {
      expect(a(len)).toBe(b(len))
    }
  })

  it('distinct 長さには相異なる色（パレット周期内）', () => {
    const colorOf = makeColorOf([100, 200, 300, 400])
    const colors = [100, 200, 300, 400].map(colorOf)
    expect(new Set(colors).size).toBe(4)
  })

  it('未知の長さはフォールバック色', () => {
    const colorOf = makeColorOf([100])
    expect(colorOf(999)).toBe('#888')
  })
})
