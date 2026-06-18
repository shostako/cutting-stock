import type { Optimality } from '../api/types'

// 正直表示: 厳密最適は緑、time_limit到達は黄(gap)。詐称しない。
export function OptimalityBadge({ o }: { o: Optimality }) {
  if (o.timed_out) {
    const gap = (o.mip_gap * 100).toFixed(1)
    return <span className="badge badge-warn">おおよそ最少（誤差 {gap}%）</span>
  }
  if (o.proven_optimal) {
    return <span className="badge badge-ok">本数は最少（確認済み）</span>
  }
  // 本数が最少でない点（段取り側へ振った解）。生ステータスは出さず材料軸の意味で表示。
  return <span className="badge badge-neutral">本数は最少ではない</span>
}

export function SetupBadge({ o }: { o: Optimality }) {
  return o.setup_proven ? (
    <span className="badge badge-ok-soft">切り方が最小（確認済み）</span>
  ) : (
    <span className="badge badge-warn">切り方の最小は未確認</span>
  )
}
