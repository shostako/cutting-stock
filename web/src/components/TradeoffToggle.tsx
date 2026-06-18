import type { ParetoFrontier } from '../api/types'
import { fmt } from '../format'

// 散布図の置換: 「原材料を最少に / 切り方を最少に」の2択セグメント + 差分1行。
// 端点2つ（material_optimal_idx / setup_optimal_idx）だけを現場語で提示する。
export function TradeoffToggle({
  frontier,
  selected,
  onSelect,
}: {
  frontier: ParetoFrontier
  selected: number
  onSelect: (i: number) => void
}) {
  const mat = frontier.solutions[frontier.material_optimal_idx]
  const setup = frontier.solutions[frontier.setup_optimal_idx]
  const isSetup = selected === frontier.setup_optimal_idx
  const dBars = setup.bars_used - mat.bars_used
  const dWaste = setup.total_waste - mat.total_waste

  return (
    <div className="tradeoff">
      <div className="tradeoff-seg">
        <button
          className={`seg-btn ${isSetup ? '' : 'active'}`}
          onClick={() => onSelect(frontier.material_optimal_idx)}
        >
          原材料を最少に
          <span className="seg-sub">{mat.bars_used}本 / 切り方{mat.num_pattern_types}通り</span>
        </button>
        <button
          className={`seg-btn ${isSetup ? 'active' : ''}`}
          onClick={() => onSelect(frontier.setup_optimal_idx)}
        >
          切り方を最少に
          <span className="seg-sub">{setup.bars_used}本 / 切り方{setup.num_pattern_types}通り</span>
        </button>
      </div>
      <p className="tradeoff-diff">
        「切り方を最少に」すると、原材料 +{dBars}本・無駄 +{fmt(dWaste)}mm で、
        切り方が {mat.num_pattern_types}通り → {setup.num_pattern_types}通り に減ります。
      </p>
    </div>
  )
}
