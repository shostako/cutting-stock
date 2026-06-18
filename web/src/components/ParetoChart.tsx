import type { ParetoFrontier } from '../api/types'

// パレート散布図（自前SVG）+ スライダ。x=パターン種類数P, y=使用本数z。
// 点は形+色で冗長エンコード（◇材料最適 / ◆段取り最少 / ●選択中 / ○その他）。色覚非依存。

const W = 320
const H = 200
const PAD = { l: 44, r: 16, t: 16, b: 36 }

export function ParetoChart({
  frontier,
  lowerBound,
  selected,
  onSelect,
}: {
  frontier: ParetoFrontier
  lowerBound: number
  selected: number
  onSelect: (i: number) => void
}) {
  const sols = frontier.solutions
  const single = sols.length <= 1

  const Ps = sols.map((s) => s.num_pattern_types)
  const Zs = sols.map((s) => s.bars_used)
  const pMin = Math.min(...Ps), pMax = Math.max(...Ps)
  const zMin = Math.min(lowerBound, ...Zs), zMax = Math.max(...Zs)

  const px = (p: number) =>
    PAD.l + (pMax === pMin ? 0.5 : (p - pMin) / (pMax - pMin)) * (W - PAD.l - PAD.r)
  const py = (z: number) =>
    H - PAD.b - (zMax === zMin ? 0.5 : (z - zMin) / (zMax - zMin)) * (H - PAD.t - PAD.b)

  return (
    <div className="pareto">
      <h3>トレードオフ（材料 ⇄ 段取り）</h3>
      {single ? (
        <p className="degenerate">
          トレードオフなし: この需要では材料最適 = 段取り最少（前線は1点）。
        </p>
      ) : null}
      <svg className="scatter" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="パレート前線">
        {/* 軸 */}
        <line x1={PAD.l} y1={H - PAD.b} x2={W - PAD.r} y2={H - PAD.b} className="axis" />
        <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={H - PAD.b} className="axis" />
        {/* 下界線 */}
        <line x1={PAD.l} y1={py(lowerBound)} x2={W - PAD.r} y2={py(lowerBound)} className="lb-line" />
        <text x={W - PAD.r} y={py(lowerBound) - 4} textAnchor="end" className="lb-label">
          下限 {lowerBound}本
        </text>
        {/* 点 */}
        {sols.map((s, i) => {
          const x = px(s.num_pattern_types)
          const y = py(s.bars_used)
          const isSel = i === selected
          const isMat = i === frontier.material_optimal_idx
          const isSetup = i === frontier.setup_optimal_idx
          return (
            <g key={i} className="pt" onClick={() => onSelect(i)} style={{ cursor: 'pointer' }}>
              {isSel && <circle cx={x} cy={y} r={9} className="pt-sel-halo" />}
              {isMat && <rect x={x - 5} y={y - 5} width={10} height={10} transform={`rotate(45 ${x} ${y})`} className="pt-mat" />}
              {isSetup && <rect x={x - 5} y={y - 5} width={10} height={10} transform={`rotate(45 ${x} ${y})`} className="pt-setup" />}
              {!isMat && !isSetup && <circle cx={x} cy={y} r={4} className="pt-other" />}
              <circle cx={x} cy={y} r={3} className={isSel ? 'pt-dot-sel' : 'pt-dot'} />
              <title>{`原材料 ${s.bars_used}本 / 切り方 ${s.num_pattern_types}種 / 廃棄 ${(s.waste_ratio * 100).toFixed(2)}%`}</title>
            </g>
          )
        })}
        {/* 軸ラベル */}
        <text x={(W + PAD.l) / 2} y={H - 6} textAnchor="middle" className="ax-label">切り方の種類</text>
        <text x={12} y={(H - PAD.b + PAD.t) / 2} textAnchor="middle" className="ax-label" transform={`rotate(-90 12 ${(H - PAD.b + PAD.t) / 2})`}>使用本数</text>
      </svg>

      <div className="slider-row">
        <span>材料最優先</span>
        <input
          type="range"
          min={0}
          max={Math.max(0, sols.length - 1)}
          step={1}
          value={selected}
          disabled={single}
          onChange={(e) => onSelect(Number(e.target.value))}
        />
        <span>段取り最少</span>
      </div>
      <div className="snap-row">
        <button className="snap" onClick={() => onSelect(frontier.material_optimal_idx)}>◇ 材料最優先</button>
        <button className="snap" onClick={() => onSelect(frontier.setup_optimal_idx)}>◆ 段取り最少</button>
      </div>
    </div>
  )
}
