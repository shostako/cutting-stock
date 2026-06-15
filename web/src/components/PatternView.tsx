import type { Solution } from '../api/types'
import { KERF_COLOR, WASTE_COLOR } from '../colors'
import { OptimalityBadge, SetupBadge } from './OptimalityBadge'
import { PatternBar } from './PatternBar'

// 選択中の解の切り方を帯で表示。色凡例 + 合計フッタ付き。
export function PatternView({
  solution,
  colorOf,
  labelOf,
}: {
  solution: Solution
  colorOf: (l: number) => string
  labelOf: (l: number) => string
}) {
  const lengths = Array.from(
    new Set(solution.patterns.flatMap((p) => p.cuts)),
  ).sort((a, b) => b - a)

  return (
    <div className="pattern-view">
      <div className="pattern-view-head">
        <h2>カットパターン</h2>
        <div className="head-metrics">
          <span>使用 {solution.bars_used}本</span>
          <span>廃棄率 {(solution.waste_ratio * 100).toFixed(2)}%</span>
          <span>種類 {solution.num_pattern_types}</span>
          <OptimalityBadge o={solution.optimality} />
          <SetupBadge o={solution.optimality} />
        </div>
      </div>

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

      <div className="pattern-list">
        {solution.patterns.map((p, i) => (
          <PatternBar key={i} pattern={p} colorOf={colorOf} />
        ))}
      </div>

      <div className="totals">
        合計: 原材料 {solution.bars_used}本 / 総廃棄 {solution.total_waste} mm / 1帯 = 原材料1本
      </div>
    </div>
  )
}
