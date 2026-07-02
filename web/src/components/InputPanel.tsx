import type { DemandRow } from '../api/types'
import { LABEL_SCHEMES, resolveLabels, type LabelScheme } from '../labels'

export interface InputState {
  length: number
  kerf: number
  demand: DemandRow[]
  labelScheme: LabelScheme   // ラベル付与方式（既定=長さ）。manual のみ手入力
}

// demo1: Wikipedia "Cutting stock problem" 製紙ロール代表例（既知最適 73本 / 廃棄0.401% / 切り方10通り）
const DEMO1: InputState = {
  length: 5600,
  kerf: 0,
  labelScheme: 'length',
  demand: [
    { length: 1380, qty: 22, label: 'A' },
    { length: 1520, qty: 25, label: 'B' },
    { length: 1560, qty: 12, label: 'C' },
    { length: 1710, qty: 14, label: 'D' },
    { length: 1820, qty: 18, label: 'E' },
    { length: 1880, qty: 18, label: 'F' },
    { length: 1930, qty: 20, label: 'G' },
    { length: 2000, qty: 10, label: 'H' },
    { length: 2050, qty: 12, label: 'I' },
    { length: 2100, qty: 14, label: 'J' },
    { length: 2140, qty: 16, label: 'K' },
    { length: 2150, qty: 18, label: 'L' },
    { length: 2200, qty: 20, label: 'M' },
  ],
}

// demo2: ランダム生成（規模を抑える: 原材料1000–2399mm / 品種3–5 / 各2–8本 / ピース≤原材料の6割）
function makeRandomDemo(): InputState {
  const length = 1000 + Math.floor(Math.random() * 1400)
  const kerf = [0, 3, 5][Math.floor(Math.random() * 3)]
  const nTypes = 3 + Math.floor(Math.random() * 3)
  const maxPiece = Math.floor(length * 0.6)
  const lengths = new Set<number>()
  let guard = 0
  while (lengths.size < nTypes && guard++ < 100) {
    const v = 150 + Math.floor(Math.random() * (maxPiece - 150))
    lengths.add(Math.round(v / 10) * 10)
  }
  const demand = Array.from(lengths)
    .sort((a, b) => b - a)
    .map((l) => ({ length: l, qty: 2 + Math.floor(Math.random() * 7), label: '' }))
  return { length, kerf, labelScheme: 'length', demand }
}

export function InputPanel({
  state,
  onChange,
  onSolve,
  loading,
  error,
  feasibility,
}: {
  state: InputState
  onChange: (s: InputState) => void
  onSolve: () => void
  loading: boolean
  error: string | null
  feasibility: string | null
}) {
  const setDemand = (i: number, patch: Partial<DemandRow>) => {
    const demand = state.demand.map((d, j) => (j === i ? { ...d, ...patch } : d))
    onChange({ ...state, demand })
  }
  const addRow = () => onChange({ ...state, demand: [...state.demand, { length: 100, qty: 1, label: '' }] })
  const removeRow = (i: number) => onChange({ ...state, demand: state.demand.filter((_, j) => j !== i) })

  const manual = state.labelScheme === 'manual'
  const shownLabels = resolveLabels(state.demand, state.labelScheme)

  return (
    <div className="input-panel">
      <div className="demo-load">
        <span className="demo-caption">デモ</span>
        <button className="demo-btn" onClick={() => onChange(DEMO1)} title="Wikipedia板取り代表例（73本 / 切り方10通り）">demo1</button>
        <button className="demo-btn" onClick={() => onChange(makeRandomDemo())} title="ランダム生成（押すたびに変わる）">demo2</button>
      </div>
      <section>
        <h2>原材料（初期設定）</h2>
        <label className="field">
          原材料長
          <input type="number" value={state.length} min={1}
            onChange={(e) => onChange({ ...state, length: Number(e.target.value) })} />
          <span className="unit">mm</span>
        </label>
        <label className="field">
          <span>カット代<span className="field-hint">（刃の厚み分）</span></span>
          <input type="number" value={state.kerf} min={0}
            onChange={(e) => onChange({ ...state, kerf: Number(e.target.value) })} />
          <span className="unit">mm</span>
        </label>
      </section>

      <section>
        <h2>需要</h2>
        <div className="label-scheme">
          <span className="ls-caption">ラベル</span>
          <div className="ls-seg">
            {LABEL_SCHEMES.map((s) => (
              <button
                key={s.key}
                className={`ls-btn ${state.labelScheme === s.key ? 'active' : ''}`}
                onClick={() => onChange({ ...state, labelScheme: s.key })}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
        <table className="demand-table">
          <thead>
            <tr><th>長さ</th><th>本数</th><th>ラベル</th><th></th></tr>
          </thead>
          <tbody>
            {state.demand.map((d, i) => (
              <tr key={i}>
                <td><input type="number" value={d.length} min={1} onChange={(e) => setDemand(i, { length: Number(e.target.value) })} /></td>
                <td><input type="number" value={d.qty} min={1} onChange={(e) => setDemand(i, { qty: Number(e.target.value) })} /></td>
                <td>
                  {manual ? (
                    <input type="text" value={d.label} maxLength={4} onChange={(e) => setDemand(i, { label: e.target.value })} />
                  ) : (
                    <span className="label-auto">{shownLabels[i]}</span>
                  )}
                </td>
                <td><button className="rm" onClick={() => removeRow(i)} aria-label="削除">✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="add-row" onClick={addRow}>＋ 行を追加</button>
      </section>

      <section>
        <button className="solve-btn" onClick={onSolve} disabled={loading}>
          {loading ? '計算中…' : '最適化を実行 ▶'}
        </button>
        {feasibility && <p className="feasibility">{feasibility}</p>}
        {error && <p className="error-banner">{error}</p>}
      </section>
    </div>
  )
}
