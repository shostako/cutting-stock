import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import type { SolveOk } from './api/types'
import { health, solve, validate } from './api/client'
import { makeColorOf } from './colors'
import { SAMPLE } from './fixtures'
import { InputPanel, type InputState } from './components/InputPanel'
import { MetricsCard } from './components/MetricsCard'
import { PatternView } from './components/PatternView'
import { computeProduction, buildPlanCsv, downloadCsv } from './report'
import { resolveLabels } from './labels'
import { fmt } from './format'

const ERROR_LABEL: Record<string, string> = {
  INFEASIBLE: '解なし',
  PIECE_TOO_LONG: 'ピースが原材料を超える',
  INVALID_INPUT: '入力エラー',
}

const INITIAL: InputState = {
  length: 1200,
  kerf: 5,
  labelScheme: 'length',
  demand: [
    { length: 500, qty: 4, label: 'A' },
    { length: 340, qty: 6, label: 'B' },
    { length: 290, qty: 5, label: 'C' },
    { length: 210, qty: 7, label: 'D' },
  ],
}

function App() {
  const [input, setInput] = useState<InputState>(INITIAL)
  // 初期表示は実ソルバ出力フィクスチャ（バックエンド未起動でも全UIが見える）
  const [result, setResult] = useState<SolveOk>(SAMPLE)
  // 解いた時点の入力（過剰生産・ラベルは結果と整合させるためこちらを基準にする）
  const [solvedInput, setSolvedInput] = useState<InputState>(INITIAL)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feasibility, setFeasibility] = useState<string | null>(null)
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [dirty, setDirty] = useState(false) // 入力が最新の結果と乖離（再計算が要る）
  const abortRef = useRef<AbortController | null>(null)

  const updateInput = (s: InputState) => {
    setInput(s)
    setDirty(true)
  }

  useEffect(() => {
    health().then(setHealthy)
  }, [])

  const labelOf = useMemo(() => {
    const m = new Map<number, string>()
    for (const d of solvedInput.demand) m.set(d.length, d.label)
    return (l: number) => m.get(l) ?? String(l)
  }, [solvedInput.demand])

  const colorOf = useMemo(() => {
    const lengths = result.solution.patterns.flatMap((p) => p.cuts)
    return makeColorOf(lengths)
  }, [result])

  const onSolve = async () => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoading(true)
    setError(null)
    setFeasibility(null)
    // スキームに応じて解決したラベルを demand に焼き込む（凡例・帯・指示書・CSV を全て一致させる）
    const labels = resolveLabels(input.demand, input.labelScheme)
    const eff: InputState = { ...input, demand: input.demand.map((d, i) => ({ ...d, label: labels[i] })) }
    try {
      const res = await solve(eff, ac.signal)
      if (res.status === 'ERROR') {
        setError(`${ERROR_LABEL[res.error.code] ?? res.error.code}: ${res.error.message}`)
      } else {
        setResult(res)
        setSolvedInput(eff)
        setDirty(false)
        try {
          const v = await validate(eff)
          setFeasibility(v.feasible ? `実行可能（最低 ${v.lower_bound_bins} 本必要）` : null)
        } catch { /* validate は補助、失敗は無視 */ }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError(`通信エラー: ${(e as Error).message}（バックエンド未起動かも）`)
    } finally {
      setLoading(false)
    }
  }

  const sol = result.solution
  const production = useMemo(() => computeProduction(solvedInput.demand, sol), [solvedInput.demand, sol])
  const hasOver = production.some((r) => r.over > 0)
  const dateStr = new Date().toLocaleDateString('ja-JP')

  const handlePrint = () => window.print()
  const handleCsv = () =>
    downloadCsv(
      'cut-plan.csv',
      buildPlanCsv({
        length: result.input_echo.length,
        kerf: result.input_echo.kerf,
        solution: sol,
        production,
      }),
    )

  return (
    <div className="app">
      <header className="app-header">
        <h1>カッティングストック最適化</h1>
        <div className="header-right">
          <span className={`health ${healthy ? 'ok' : healthy === false ? 'ng' : ''}`}>
            {healthy ? '● API接続' : healthy === false ? '○ API未接続(fixture表示)' : '…'}
          </span>
          <span className="meta">{result.meta?.material_solver}</span>
        </div>
      </header>

      <div className="layout">
        <aside className="left">
          <InputPanel
            state={input}
            onChange={updateInput}
            onSolve={onSolve}
            loading={loading}
            error={error}
            feasibility={feasibility}
          />
          <MetricsCard solution={sol} lowerBound={result.lower_bound_bins} />
        </aside>

        <main className="right">
          <div className="print-only print-head">
            <h2>カット指示書</h2>
            <p className="print-date">{dateStr}</p>
            <ul className="print-summary">
              <li>原材料長: {result.input_echo.length} mm</li>
              <li>カット代: {result.input_echo.kerf} mm</li>
              <li>必要原材料: {sol.bars_used} 本</li>
              <li>総廃棄: {fmt(sol.total_waste)} mm（{(sol.waste_ratio * 100).toFixed(2)}%）</li>
              <li>切り方の数: {sol.num_pattern_types} 通り</li>
            </ul>
          </div>
          <div className="right-toolbar">
            <h2>カットパターン</h2>
            <div className="report-actions">
              <button className="report-btn" onClick={handlePrint}>印刷</button>
              <button className="report-btn" onClick={handleCsv}>CSVで書き出し</button>
            </div>
          </div>
          {dirty && (
            <div className="stale-banner">
              入力が変わりました。「最適化を実行」で再計算してください（下は前回の結果）。
            </div>
          )}
          <div className={dirty ? 'stale-content' : undefined}>
            <PatternView solution={sol} colorOf={colorOf} labelOf={labelOf} />
          </div>
          <div className="overproduction">
            {hasOver ? (
              <>
                <h3 className="over-title">過剰生産（廃棄に計上されます）</h3>
                <table className="over-table">
                  <thead>
                    <tr><th>品目</th><th>長さ</th><th>需要</th><th>生産</th><th>過剰</th></tr>
                  </thead>
                  <tbody>
                    {production.filter((r) => r.over > 0).map((r) => (
                      <tr key={r.length}>
                        <td>{r.label || r.length}</td>
                        <td>{r.length} mm</td>
                        <td>{r.demand}</td>
                        <td>{r.produced}</td>
                        <td className="over-cell">+{r.over}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="over-none">過剰生産なし（需要ぴったり）</p>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
