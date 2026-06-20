// バックエンド(solver.api / http.py)の入出力契約。docs/SOLVER_DESIGN.md「ローカルAPI」節準拠。

export type SegmentKind = 'piece' | 'kerf' | 'waste'

export interface Segment {
  kind: SegmentKind
  offset: number
  length: number
  item_length: number | null
  label: string
}

export interface Pattern {
  cuts: number[]
  item_counts: Record<string, number> // キーは文字列（実コード準拠）
  stock_length: number
  waste: number
  run_count: number
  segments: Segment[]
}

export interface Optimality {
  status: string
  mip_gap: number
  lp_lower_bound: number | null
  proven_optimal: boolean        // 使用本数が最小（材料軸 gap=0）
  patterns_min_proven: boolean   // その本数で切り方の種類数も最小（CP-SAT 証明）
  timed_out: boolean
}

export interface Solution {
  bars_used: number
  total_waste: number
  waste_ratio: number
  num_pattern_types: number
  optimality: Optimality
  patterns: Pattern[]
}

export interface SolveOk {
  status: 'OK'
  validation: string[]
  input_echo: { length: number; kerf: number; total_demand_length: number }
  lower_bound_bins: number
  solution: Solution   // 材料最適の単一解（段取り軸は pattern-stock へ分離）
  meta: Record<string, string>
}

export interface SolveErr {
  status: 'ERROR'
  error: { code: string; message: string }
}

export type SolveResponse = SolveOk | SolveErr

export interface ValidateResponse {
  status: string
  feasible: boolean
  lower_bound_bins?: number
  code?: string
  message?: string
}

export interface DemandRow {
  length: number
  qty: number
  label: string
}
