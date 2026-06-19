import type { Solution } from '../api/types'
import { fmt, pct } from '../format'
import { OptimalityBadge } from './OptimalityBadge'

export function MetricsCard({
  solution,
  lowerBound,
}: {
  solution: Solution
  lowerBound: number
}) {
  return (
    <div className="metrics-card">
      <h3>この計画</h3>
      <table>
        <tbody>
          <tr>
            <th>使用本数</th>
            <td>{solution.bars_used} 本<span className="lb">（最低 {lowerBound} 本）</span></td>
          </tr>
          <tr><th>総廃棄</th><td>{fmt(solution.total_waste)} mm</td></tr>
          <tr><th>廃棄率</th><td>{pct(solution.waste_ratio)}</td></tr>
          <tr><th>切り方の数</th><td>{solution.num_pattern_types} 通り</td></tr>
          <tr><th>最適性</th><td><OptimalityBadge o={solution.optimality} /></td></tr>
        </tbody>
      </table>
    </div>
  )
}
