# 変更履歴

このリポジトリの主な変更を新しい順に書く。日付は日本時間。

## 2026-10-22

### セキュリティ
- 脆弱性のある部品を更新した（#4）。Hugging Face の Space にも反映した（コミット bad84f9）。
  - Python: anyio 4.13.0 → 4.14.2、certifi 2026.5.20 → 2026.10.19（同梱していた emSign のルート証明書の配下に、秘密鍵が漏れた中間 CA が 8 つあった。GHSA-6q48-6c7w-9gw2）。`pip-audit` は 3 件から 0 件になった。Space に入っていたのは anyio だけで、certifi は開発用の httpx 経由だった。
  - 画面（`web/`）: vite 8.3.5、vitest 4.1.12、postcss 8.5.31 など開発用の部品。`npm audit` は 9 件（high 6・moderate 3、開発用のみ）から 0 件になった。
