import type { DemandRow } from '../api/types'

export interface InputState {
  length: number
  kerf: number
  demand: DemandRow[]
  maxExtra: number
  advanced: boolean   // 「切り方を減らすため余分に使う」高度モード（既定OFF）
}

// Wikipedia "Cutting stock problem" 製紙ロール代表例（既知最適 73本 / 0.401% / 切り方10種）
const WIKIPEDIA_EXAMPLE: InputState = {
  length: 5600,
  kerf: 0,
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
  maxExtra: 1,
  advanced: true,   // 例題はトレードオフ（切り方10⇄8）を見せたいので高度モードON
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

  return (
    <div className="input-panel">
      <div className="example-load">
        <button className="example-btn" onClick={() => onChange(WIKIPEDIA_EXAMPLE)}>
          Wikipedia板取り例題を読み込む
        </button>
      </div>
      <section>
        <h2>原材料（初期設定）</h2>
        <label className="field">
          原材料長 L
          <input type="number" value={state.length} min={1}
            onChange={(e) => onChange({ ...state, length: Number(e.target.value) })} />
          <span className="unit">mm</span>
        </label>
        <label className="field">
          カット代 k
          <input type="number" value={state.kerf} min={0}
            onChange={(e) => onChange({ ...state, kerf: Number(e.target.value) })} />
          <span className="unit">mm</span>
        </label>
        <p className="note">※ 1カット = 切るたび k を消費（Model A）</p>
      </section>

      <section>
        <h2>需要</h2>
        <table className="demand-table">
          <thead>
            <tr><th>長さ</th><th>本数</th><th>ラベル</th><th></th></tr>
          </thead>
          <tbody>
            {state.demand.map((d, i) => (
              <tr key={i}>
                <td><input type="number" value={d.length} min={1} onChange={(e) => setDemand(i, { length: Number(e.target.value) })} /></td>
                <td><input type="number" value={d.qty} min={1} onChange={(e) => setDemand(i, { qty: Number(e.target.value) })} /></td>
                <td><input type="text" value={d.label} maxLength={4} onChange={(e) => setDemand(i, { label: e.target.value })} /></td>
                <td><button className="rm" onClick={() => removeRow(i)} aria-label="削除">✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="add-row" onClick={addRow}>＋ 行を追加</button>
      </section>

      <section>
        <label className="advanced-check">
          <input
            type="checkbox"
            checked={state.advanced}
            onChange={(e) =>
              onChange({
                ...state,
                advanced: e.target.checked,
                maxExtra: e.target.checked ? Math.max(1, state.maxExtra) : state.maxExtra,
              })
            }
          />
          切り方の数をもっと減らしたい（原材料を少し多めに使ってよい）
        </label>
        {state.advanced && (
          <div className="advanced-body">
            <p className="note">原材料を少し多めに使うほど、切り替え（段取り）の手間を減らせる場合があります。</p>
            <label className="field">
              原材料を最大
              <input type="number" value={state.maxExtra} min={1} max={10}
                onChange={(e) => onChange({ ...state, maxExtra: Number(e.target.value) })} />
              <span className="unit">本まで多めに</span>
            </label>
          </div>
        )}
        <button className="solve-btn" onClick={onSolve} disabled={loading}>
          {loading ? '計算中…' : '最適化を実行 ▶'}
        </button>
        {feasibility && <p className="feasibility">{feasibility}</p>}
        {error && <p className="error-banner">{error}</p>}
      </section>
    </div>
  )
}
