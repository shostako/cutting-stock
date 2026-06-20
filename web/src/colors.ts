// 業務トーンの離散パレット（彩度を抑えた色覚配慮寄り）。長さ別に安定割当（同じ長さは常に同色）。

const PALETTE = [
  '#4e79a7', '#59a14f', '#e1853a', '#9c6ade',
  '#76b7b2', '#b07aa1', '#cf9c1d', '#5a6b7b',
  '#86bcb6', '#d37295', '#a0743a', '#79706e',
]

// kerf/waste 色はテーマ追従のため CSS 変数 --kerf / --waste（index.css）へ移管。

export function makeColorOf(lengths: number[]): (length: number) => string {
  const sorted = Array.from(new Set(lengths)).sort((a, b) => a - b)
  const map = new Map<number, string>()
  sorted.forEach((l, i) => map.set(l, PALETTE[i % PALETTE.length]))
  return (length: number) => map.get(length) ?? '#888'
}
