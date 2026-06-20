import type { Pattern, Segment } from '../api/types'
import { fmt } from '../format'

// 比率忠実バー: 各 segment を left=offset/L%, width=length/L% の絶対配置 div で描く。
// 数値→比率の線形マップのみ（フロント演算ゼロの精神）。length合計=stock_length は API 保証。
// kerf は実寸だと見えないので min-width で最小視認幅を持たせる（凡例に注記）。文字は歪まない。

function fillOf(seg: Segment, colorOf: (l: number) => string): string {
  if (seg.kind === 'piece') return colorOf(seg.item_length as number)
  if (seg.kind === 'kerf') return 'var(--kerf)'   // テーマ追従（index.css）
  return 'var(--waste)'
}

export function PatternBar({ pattern, colorOf }: { pattern: Pattern; colorOf: (l: number) => string }) {
  const L = pattern.stock_length
  const pct = (v: number) => `${(v / L) * 100}%`

  // dev アサート: Σsegment.length === stock_length（API 不変量の二重確認）
  if (import.meta.env.DEV) {
    const sum = pattern.segments.reduce((a, s) => a + s.length, 0)
    if (sum !== L) console.warn(`segments sum ${sum} != stock_length ${L}`, pattern)
  }

  return (
    <div className="pattern">
      <div className="pattern-meta">
        <span className="pattern-cuts">{pattern.cuts.join(' + ')} mm</span>
        <span className="pattern-run">×{pattern.run_count}本</span>
        <span className="pattern-waste">残材 {fmt(pattern.waste)} mm</span>
      </div>
      <div className="bar">
        {pattern.segments.map((s, i) => (
          <div
            key={i}
            className={`seg seg-${s.kind}`}
            style={{ left: pct(s.offset), width: pct(s.length), background: fillOf(s, colorOf) }}
            title={
              s.kind === 'piece'
                ? `${s.label || s.item_length}: ${s.length}mm`
                : s.kind === 'kerf'
                  ? `カット代 ${s.length}mm`
                  : `残材 ${s.length}mm`
            }
          >
            {s.kind === 'piece' && s.length > L * 0.06 && (
              <span className="seg-label">{s.label || s.item_length}</span>
            )}
          </div>
        ))}
      </div>
      <div className="bar-scale">
        <span>0</span>
        <span>{fmt(L)} mm</span>
      </div>
    </div>
  )
}
