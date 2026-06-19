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
  // 証明が立たなかった稀ケース（time_limit 以外）。詐称せず中立表示。
  return <span className="badge badge-neutral">本数は最少ではない可能性</span>
}
