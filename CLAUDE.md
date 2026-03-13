# wp-auto-poster — Claude Code 向けプロジェクトガイド

## コマンド

### セットアップ（初回のみ）
```bash
cd wp-auto-poster
uv sync
uv run playwright install chromium
```

### WordPress 接続確認
```bash
cd wp-auto-poster
uv run python lib/wp_client.py --action check
```

### 記事の自動生成・投稿（メイン用途）
```
/generate-post <テーマ>        # 記事執筆〜WordPress下書き投稿まで全自動
/git-push                      # git add → commit → push
```

### 個別 Python スクリプト
```bash
uv run python lib/wp_client.py --action publish --draft-dir ../drafts/{slug}/
uv run python lib/wp_client.py --action update --post-id {id} --draft-dir ../drafts/{slug}/
uv run python lib/image_client.py --request ../drafts/{slug}/image_requests.json --output ../drafts/{slug}/images/
uv run python lib/mermaid_renderer.py --request ../drafts/{slug}/image_requests.json --output ../drafts/{slug}/images/
uv run python lib/screenshot_capturer.py --url https://example.com --output screenshot.png
```

## アーキテクチャ

Claude Code Skills がエージェントをオーケストレートして WordPress へ自動投稿するシステム。

```
ClaudeCodeWork/
├── wp-auto-poster/lib/        # Python ライブラリ本体
├── .claude/skills/            # Claude Code スキル定義（git 管理）
├── .claude/agents/            # Claude Code エージェント定義（git 管理）
├── drafts/                    # 生成記事ワークスペース（gitignore）
├── gemini_images/             # Gemini 画像生成結果
└── reports/                   # 分析レポート
```

## 利用可能なスキル

| スキル | 用途 |
|--------|------|
| `/generate-post <テーマ>` | 記事執筆→画像生成→SEO→WP投稿の全自動 |
| `/update-post <post_id> [slug]` | 既存WP記事をdrafts/の内容で更新 |
| `/wp-affiliate-linker <テーマ or slug>` | 書籍アフィリエイトリンクを単体生成 |
| `/git-push ["メッセージ"]` | git add → commit → push |
| `/gemini-image <テーマ>` | Gemini でアイキャッチ・挿絵を生成 |
| `/blog-analytics` | GA4 + Search Console の現状分析 |

## 環境変数（wp-auto-poster/.env）

```
WP_URL, WP_USER, WP_APP_PASSWORD  # WordPress REST API
GOOGLE_API_KEY                     # Gemini 画像生成
MOSHIMO_AMAZON_AID, MOSHIMO_RAKUTEN_AID  # もしもアフィリエイト
MOSHIMO_AMAZON_PLID=27060, MOSHIMO_RAKUTEN_PLID=27059
```

## Gotchas

- Python は必ず `uv run python` 経由で実行（直接 `python` は venv 外）
- `cd wp-auto-poster` してから実行（.env の読み込みパスが相対パス）
- `drafts/` と `logs/` は gitignore — コミット不要・自動生成物
- WordPress 投稿は**必ず下書き**で作成。公開は人間が行う
- `uv.lock` は再現性のため git 管理対象
- `.claude/settings.local.json` は gitignore（個人設定）
