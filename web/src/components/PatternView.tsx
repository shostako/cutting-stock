import type { Solution } from '../api/types'
import { KERF_COLOR, WASTE_COLOR } from '../colors'
import { fmt } from '../format'
import { OptimalityBadge, PatternsBadge } from './OptimalityBadge'
import { PatternBar } from './PatternBar'

// 色凡例（piece 長さ別 + kerf + waste）。単体表示でも比較モードの共有凡例でも使う。
export function Legend({
  lengths,
  colorOf,
  labelOf,
}: {
  lengths: number[]
  colorOf: (l: number) => string
  labelOf: (l: number) => string
}) {
  return (
    <div className="legend">
      {lengths.map((l) => (
        <span className="legend-item" key={l}>
          <span className="swatch" style={{ background: colorOf(l) }} />
          {labelOf(l) || l}:{l}
        </span>
      ))}
      <span className="legend-item">
        <span className="swatch" style={{ background: KERF_COLOR }} />
        カット代（視認のため最小幅）
      </span>
      <span className="legend-item">
        <span className="swatch" style={{ background: WASTE_COLOR }} />
        残材
      </span>
    </div>
  )
}

// 解の切り方を帯で表示。title=レーン見出し（比較モード用）。showLegend=false で凡例を外す（共有時）。
export function PatternView({
  solution,
  colorOf,
  labelOf,
  title,
  showLegend = true,
}: {
  solution: Solution
  colorOf: (l: number) => string
  labelOf: (l: number) => string
  title?: string
  showLegend?: boolean
}) {
  const lengths = Array.from(new Set(solution.patterns.flatMap((p) => p.cuts))).sort((a, b) => b - a)

  return (
    <div className="pattern-view">
      <div className="pattern-view-head">
        {title ? <h3 className="lane-title">{title}</h3> : null}
        <div className="head-metrics">
          <span>使用 {solution.bars_used}本</span>
          <span>廃棄率 {(solution.waste_ratio * 100).toFixed(2)}%</span>
          <span>切り方 {solution.num_pattern_types}通り</span>
          <OptimalityBadge o={solution.optimality} />
          <PatternsBadge o={solution.optimality} />
        </div>
      </div>

      {showLegend && <Legend lengths={lengths} colorOf={colorOf} labelOf={labelOf} />}

      <div className="pattern-list">
        {solution.patterns.map((p, i) => (
          <PatternBar key={i} pattern={p} colorOf={colorOf} />
        ))}
      </div>

      <div className="totals">
        合計: 原材料 {solution.bars_used}本 / 総廃棄 {fmt(solution.total_waste)} mm / 1帯 = 原材料1本
      </div>
    </div>
  )
}
