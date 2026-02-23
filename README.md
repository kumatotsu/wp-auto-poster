# wp-auto-poster

**Claude Code Skills + Agent Teams** を使った WordPress 記事自動生成・投稿システムです。
テーマを指定するだけで、記事執筆・画像生成・SEO最適化・WordPress下書き投稿まで全自動で行います。

## 機能

| 機能 | 詳細 |
|------|------|
| 📝 記事執筆 | Claude (Sonnet) が Web リサーチして SEO 最適化記事を生成 |
| 🎨 画像生成 | Gemini API (Nano Banana Pro/Flash) でアイキャッチ・挿絵を生成 |
| 📊 図解生成 | Mermaid でフローチャート・構成図を自動描画 |
| 📸 スクリーンショット | Playwright でWebサービスの画面をキャプチャして記事に挿入 |
| 🔍 SEO最適化 | Yoast SEO 向けメタデータ（タイトル・ディスクリプション・キーワード）を自動生成 |
| 📤 WordPress投稿 | REST API 経由で下書き投稿（公開は人間が行う） |

## システム構成

```
ClaudeCodeWork/
├── wp-auto-poster/          # Python ライブラリ本体
│   ├── lib/
│   │   ├── config.py        # 設定管理（.env 読み込み）
│   │   ├── wp_client.py     # WordPress REST API クライアント
│   │   ├── image_client.py  # Gemini API 画像生成
│   │   ├── mermaid_renderer.py  # Mermaid 図解レンダリング
│   │   └── screenshot_capturer.py  # Playwright スクリーンショット
│   ├── templates/           # Gutenberg ブロックテンプレート
│   └── pyproject.toml       # 依存関係管理（uv）
├── .claude/
│   ├── agents/              # Claude Code エージェント定義
│   │   ├── wp-article-writer/   # 記事執筆エージェント
│   │   ├── wp-image-generator/  # 画像生成エージェント
│   │   ├── wp-seo-reviewer/     # SEO レビューエージェント
│   │   └── wp-publisher/        # WordPress 投稿エージェント
│   └── skills/              # Claude Code スキル定義
│       ├── generate-post/   # /generate-post スキル
│       └── git-push/        # /git-push スキル（コミット＆プッシュ自動化）
└── research/                # リサーチノート
```

## 必要条件

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー
- Node.js（Mermaid CLI 用）
- Claude Code
- Google Gemini API キー
- WordPress サイト（アプリケーションパスワード設定済み）

## セットアップ

### 1. 依存関係インストール

```bash
cd wp-auto-poster
uv sync
uv run playwright install chromium
```

### 2. 環境変数設定

```bash
cp .env.example .env
```

`.env` を編集:

```env
WP_URL=https://your-wordpress-site.com
WP_USER=your-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
GOOGLE_API_KEY=AIza...
```

### 3. 接続確認

```bash
cd wp-auto-poster
uv run python lib/wp_client.py --action check
```

## 使い方

### 記事の自動生成・投稿

Claude Code で以下のスキルを実行:

```
/generate-post Claude Codeで始めるAI自動化入門
```

自動で以下が実行されます：
1. Web リサーチで最新情報収集
2. SEO 最適化記事執筆（article.html）
3. 画像・図解・スクリーンショット生成
4. SEO メタデータ最適化
5. WordPress に下書き投稿

### 個別コマンド

```bash
# WordPress 接続テスト
uv run python lib/wp_client.py --action check

# 下書き投稿
uv run python lib/wp_client.py --action publish --draft-dir ../drafts/slug/

# 記事更新
uv run python lib/wp_client.py --action update --post-id 763 --draft-dir ../drafts/slug/

# 画像生成
uv run python lib/image_client.py --request ../drafts/slug/image_requests.json --output ../drafts/slug/images/

# Mermaid 図解生成
uv run python lib/mermaid_renderer.py --request ../drafts/slug/image_requests.json --output ../drafts/slug/images/

# スクリーンショット取得
uv run python lib/screenshot_capturer.py --url https://claude.ai --output screenshot.png
```

## ワークフロー

```
/generate-post <テーマ>
        │
        ▼
[wp-article-writer]  ── Web リサーチ → 記事執筆
        │
        ▼
[並列実行]
  ├── [wp-image-generator]  ── Gemini + Mermaid + Playwright
  └── [wp-seo-reviewer]     ── SEO メタデータ生成
        │
        ▼
[wp-publisher]  ── WordPress 下書き投稿
```

## コード変更時のルール

このプロジェクトでは **コードを変更したら必ず git commit & push** します。

```
/git-push  ← Claude Code スキルで自動化
```

## ライセンス

MIT
