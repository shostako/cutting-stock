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
  proven_optimal: boolean
  setup_proven: boolean
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

export interface ParetoFrontier {
  material_optimal_idx: number
  setup_optimal_idx: number
  recommended_index: number
  solutions: Solution[]
}

export interface SolveOk {
  status: 'OK'
  validation: string[]
  input_echo: { length: number; kerf: number; total_demand_length: number }
  lower_bound_bins: number
  pareto: ParetoFrontier
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
