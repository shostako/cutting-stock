import type { ParetoFrontier } from '../api/types'
import { Legend, PatternView } from './PatternView'

// 比較モード: 材料最優先と段取り最少の2解を同一スケール（各帯 viewBox=stock_length・幅100%）で並置。
// 共有凡例を1つだけ上に出し、2レーンは凡例なしの PatternView で揃える。
export function ComparePanel({
  frontier,
  colorOf,
  labelOf,
}: {
  frontier: ParetoFrontier
  colorOf: (l: number) => string
  labelOf: (l: number) => string
}) {
  const mat = frontier.solutions[frontier.material_optimal_idx]
  const setup = frontier.solutions[frontier.setup_optimal_idx]
  const lengths = Array.from(
    new Set([...mat.patterns, ...setup.patterns].flatMap((p) => p.cuts)),
  ).sort((a, b) => b - a)

  return (
    <div className="compare">
      <Legend lengths={lengths} colorOf={colorOf} labelOf={labelOf} />
      <div className="compare-lanes">
        <div className="lane">
          <PatternView solution={mat} colorOf={colorOf} labelOf={labelOf} title="◇ 材料最優先" showLegend={false} />
        </div>
        <div className="lane">
          <PatternView solution={setup} colorOf={colorOf} labelOf={labelOf} title="◆ 段取り最少" showLegend={false} />
        </div>
      </div>
    </div>
  )
}
