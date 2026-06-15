import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import type { SolveOk } from './api/types'
import { health, solve, validate } from './api/client'
import { makeColorOf } from './colors'
import { SAMPLE } from './fixtures'
import { InputPanel, type InputState } from './components/InputPanel'
import { ParetoChart } from './components/ParetoChart'
import { MetricsCard } from './components/MetricsCard'
import { PatternView } from './components/PatternView'

const ERROR_LABEL: Record<string, string> = {
  INFEASIBLE: '解なし',
  PIECE_TOO_LONG: 'ピースが原材料を超える',
  INVALID_INPUT: '入力エラー',
}

const INITIAL: InputState = {
  length: 1200,
  kerf: 5,
  demand: [
    { length: 500, qty: 4, label: 'A' },
    { length: 340, qty: 6, label: 'B' },
    { length: 290, qty: 5, label: 'C' },
    { length: 210, qty: 7, label: 'D' },
  ],
  maxExtra: 3,
}

function App() {
  const [input, setInput] = useState<InputState>(INITIAL)
  // 初期表示は実ソルバ出力フィクスチャ（バックエンド未起動でも全UIが見える）
  const [result, setResult] = useState<SolveOk>(SAMPLE)
  const [selected, setSelected] = useState<number>(SAMPLE.pareto.recommended_index)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feasibility, setFeasibility] = useState<string | null>(null)
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    health().then(setHealthy)
  }, [])

  const labelOf = useMemo(() => {
    const m = new Map<number, string>()
    for (const d of input.demand) m.set(d.length, d.label)
    return (l: number) => m.get(l) ?? ''
  }, [input.demand])

  const colorOf = useMemo(() => {
    const lengths = result.pareto.solutions.flatMap((s) => s.patterns.flatMap((p) => p.cuts))
    return makeColorOf(lengths)
  }, [result])

  const onSolve = async () => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoading(true)
    setError(null)
    setFeasibility(null)
    try {
      const res = await solve(input, ac.signal)
      if (res.status === 'ERROR') {
        setError(`${ERROR_LABEL[res.error.code] ?? res.error.code}: ${res.error.message}`)
      } else {
        setResult(res)
        setSelected(res.pareto.recommended_index)
        try {
          const v = await validate(input)
          setFeasibility(v.feasible ? `実行可能（下界 ${v.lower_bound_bins} 本）` : null)
        } catch { /* validate は補助、失敗は無視 */ }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError(`通信エラー: ${(e as Error).message}（バックエンド未起動かも）`)
    } finally {
      setLoading(false)
    }
  }

  const sol = result.pareto.solutions[selected] ?? result.pareto.solutions[0]

  return (
    <div className="app">
      <header className="app-header">
        <h1>カッティングストック最適化</h1>
        <div className="header-right">
          <span className={`health ${healthy ? 'ok' : healthy === false ? 'ng' : ''}`}>
            {healthy ? '● API接続' : healthy === false ? '○ API未接続(fixture表示)' : '…'}
          </span>
          <span className="meta">{result.meta?.material_solver} / {result.meta?.setup_solver}</span>
        </div>
      </header>

      <div className="layout">
        <aside className="left">
          <InputPanel
            state={input}
            onChange={setInput}
            onSolve={onSolve}
            loading={loading}
            error={error}
            feasibility={feasibility}
          />
          <ParetoChart
            frontier={result.pareto}
            lowerBound={result.lower_bound_bins}
            selected={selected}
            onSelect={setSelected}
          />
          <MetricsCard solution={sol} lowerBound={result.lower_bound_bins} />
        </aside>

        <main className="right">
          <PatternView solution={sol} colorOf={colorOf} labelOf={labelOf} />
        </main>
      </div>
    </div>
  )
}

export default App
