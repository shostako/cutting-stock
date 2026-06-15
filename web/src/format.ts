// 数値整形（mm の桁区切り・廃棄率）。
export const fmt = (n: number) => n.toLocaleString('ja-JP')
export const pct = (ratio: number) => `${(ratio * 100).toFixed(2)} %`
