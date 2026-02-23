# WordPress記事自動投稿 実装計画書 v2

## Skills + Agent Teams + 画像生成 統合アーキテクチャ

**更新日:** 2026-02-22
**前版からの主な変更:**
- トリガーを Python スクリプト → Claude Code Skills に変更
- Agent Teams による並列処理を導入
- Gemini API（Nano Banana / Pro）による画像生成機能を追加
- Mermaid による図解生成機能を追加
- Python の役割を「外部API通信」のみに限定

---

## 1. システムアーキテクチャ

### 全体フロー

```
ユーザー
  │
  │  /generate-post "Claude Codeとは？完全解説"
  ▼
┌─────────────────────────────────────────────────────────┐
│  Claude Code Skill: generate-post                       │
│  （トリガー・オーケストレーター）                          │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Agent Team: wp-post-generation                  │    │
│  │                                                   │    │
│  │  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │ 記事執筆Agent │  │ 画像生成Agent │  ← 並列実行  │    │
│  │  │ (wp-article-  │  │ (wp-image-   │              │    │
│  │  │  writer)      │  │  generator)  │              │    │
│  │  └──────┬───────┘  └──────┬───────┘              │    │
│  │         │                  │                       │    │
│  │         ▼                  ▼                       │    │
│  │  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │ SEOレビュー   │  │ 図解生成     │  ← 並列実行  │    │
│  │  │ Agent        │  │ (Mermaid)    │              │    │
│  │  │ (wp-seo-     │  │              │              │    │
│  │  │  reviewer)   │  │              │              │    │
│  │  └──────┬───────┘  └──────┬───────┘              │    │
│  │         │                  │                       │    │
│  │         ▼                  ▼                       │    │
│  │  ┌────────────────────────────────┐               │    │
│  │  │ 投稿Agent (wp-publisher)       │               │    │
│  │  │ Python → WordPress REST API    │               │    │
│  │  └────────────────────────────────┘               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
               WordPress (m-totsu.com)
               下書きとして保存
                        │
                        ▼
               人間が確認 → 「公開」ボタン
```

### Python の役割（最小化）

| 旧（v1） | 新（v2） |
|-----------|---------|
| `generate.py` → Claude API呼び出し | **不要**（Claude Code自身が記事執筆） |
| `review.py` → ターミナルUI | **不要**（Agent内でSEOレビュー） |
| `publish.py` → WordPress REST API | `lib/wp_client.py`（API通信のみ） |
| なし | `lib/image_client.py`（Gemini API通信） |
| なし | `lib/mermaid_renderer.py`（Mermaid→PNG変換） |

---

## 2. ディレクトリ構成

```
ClaudeCodeWork/
├── .claude/
│   ├── skills/
│   │   └── generate-post/
│   │       └── SKILL.md              # メインのトリガースキル
│   ├── agents/
│   │   ├── wp-article-writer/
│   │   │   └── wp-article-writer.md  # 記事執筆エージェント
│   │   ├── wp-image-generator/
│   │   │   └── wp-image-generator.md # 画像生成エージェント
│   │   ├── wp-seo-reviewer/
│   │   │   └── wp-seo-reviewer.md    # SEOレビューエージェント
│   │   └── wp-publisher/
│   │       └── wp-publisher.md       # WordPress投稿エージェント
│   └── CLAUDE.md                     # プロジェクト設定
│
├── wp-auto-poster/
│   ├── .env                          # 認証情報（Git管理外）
│   ├── .env.example                  # テンプレート
│   ├── .gitignore
│   ├── requirements.txt
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── config.py                 # 設定読み込み
│   │   ├── wp_client.py              # WordPress REST API クライアント
│   │   ├── image_client.py           # Gemini API 画像生成クライアント
│   │   └── mermaid_renderer.py       # Mermaid → PNG 変換
│   ├── prompts/
│   │   ├── article_system.txt        # 記事生成のシステムプロンプト
│   │   ├── image_eyecatch.txt        # アイキャッチ画像プロンプトテンプレート
│   │   ├── image_illustration.txt    # 挿絵プロンプトテンプレート
│   │   └── seo_review.txt            # SEOレビュープロンプト
│   ├── templates/
│   │   └── cocoon_blocks.py          # Cocoon用HTMLブロック生成ヘルパー
│   ├── mermaid-config.json           # Mermaid描画設定（日本語フォント等）
│   └── tests/
│       ├── test_wp_client.py
│       ├── test_image_client.py
│       └── test_mermaid_renderer.py
│
├── drafts/                           # 生成済み下書き（Git管理外）
│   └── {slug}/
│       ├── article.html              # 記事HTML
│       ├── meta.json                 # SEOメタデータ
│       └── images/
│           ├── eyecatch.png          # アイキャッチ画像
│           ├── illustration_1.png    # 挿絵1
│           ├── illustration_2.png    # 挿絵2
│           └── diagram_1.png         # Mermaid図解
│
├── logs/                             # 投稿ログ（Git管理外）
└── research/                         # 調査資料（参考）
    ├── gemini-api-research.md
    ├── wordpress-api-research.md
    ├── claude-skills-agents-research.md
    └── mermaid-research.md
```

---

## 3. Skills & Agents 定義

### 3.1 Skill: generate-post

**ファイル:** `.claude/skills/generate-post/SKILL.md`

```yaml
---
name: generate-post
description: "WordPress記事を自動生成して下書き投稿する。/generate-post <テーマ> で呼び出す"
allowed-tools:
  - Task
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - TodoWrite
context: fork
---
```

**Markdown本文の概要:**

1. `$ARGUMENTS[0]` からテーマを取得
2. `drafts/{date}_{slug}/` ディレクトリを作成
3. 以下のエージェントをTaskツールで並列起動:
   - `wp-article-writer` → 記事HTML生成
   - `wp-image-generator` → 画像生成（Gemini API + Mermaid）
4. 記事・画像の完成後:
   - `wp-seo-reviewer` → SEOメタデータ最適化
5. 全て完成後:
   - `wp-publisher` → WordPress REST API で下書き投稿
6. 結果をユーザーに報告（下書きURL、画像一覧、SEOスコア）

### 3.2 Agent: wp-article-writer

**ファイル:** `.claude/agents/wp-article-writer/wp-article-writer.md`

```yaml
---
name: wp-article-writer
description: "WordPress（Cocoonテーマ）向けの技術ブログ記事をHTML形式で執筆する"
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
model: sonnet
permissionMode: acceptEdits
---
```

**役割:**
- 指定テーマに基づいて3,000〜5,000文字の記事を執筆
- Cocoonテーマ対応のHTML（Gutenbergブロック形式）で出力
- H2: 3〜5個、H3: 各H2の下に2〜3個
- 挿絵・図解の挿入位置を `<!-- IMAGE_PLACEHOLDER: {description} -->` で指定
- `drafts/{slug}/article.html` に保存
- `drafts/{slug}/image_requests.json` に画像生成リクエストを出力

**image_requests.json の形式:**
```json
{
  "eyecatch": {
    "prompt": "ブログのアイキャッチ: ...",
    "style": "モダンでクリーンなデザイン"
  },
  "illustrations": [
    {
      "id": "illust_1",
      "prompt": "...",
      "alt": "Claude Codeの操作画面",
      "caption": "...",
      "insert_after": "h2_1"
    }
  ],
  "diagrams": [
    {
      "id": "diagram_1",
      "mermaid_code": "flowchart TD\n  A-->B-->C",
      "alt": "システム構成図",
      "caption": "...",
      "insert_after": "h2_3"
    }
  ]
}
```

### 3.3 Agent: wp-image-generator

**ファイル:** `.claude/agents/wp-image-generator/wp-image-generator.md`

```yaml
---
name: wp-image-generator
description: "Gemini API（Nano Banana）とMermaidを使ってブログ用画像を生成する"
tools:
  - Read
  - Write
  - Bash
  - Glob
model: sonnet
permissionMode: acceptEdits
---
```

**役割:**
- `drafts/{slug}/image_requests.json` を読み込み
- アイキャッチ → Gemini API（Nano Banana Pro, 2K, 16:9）
- 挿絵 → Gemini API（Nano Banana Flash, 4:3）
- 図解 → Mermaid CLI（mmdc → PNG）
- 生成画像を `drafts/{slug}/images/` に保存
- `drafts/{slug}/image_results.json` に生成結果を出力

**実行コマンド例:**
```bash
# Gemini API画像生成
python wp-auto-poster/lib/image_client.py \
  --request drafts/{slug}/image_requests.json \
  --output drafts/{slug}/images/

# Mermaid図解生成
python wp-auto-poster/lib/mermaid_renderer.py \
  --request drafts/{slug}/image_requests.json \
  --output drafts/{slug}/images/
```

### 3.4 Agent: wp-seo-reviewer

**ファイル:** `.claude/agents/wp-seo-reviewer/wp-seo-reviewer.md`

```yaml
---
name: wp-seo-reviewer
description: "記事のSEOメタデータ・内部リンク・キーワード密度を最適化する"
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
model: haiku
permissionMode: acceptEdits
---
```

**役割:**
- `drafts/{slug}/article.html` を読み込みSEO分析
- タイトル（32文字以内）、メタディスクリプション（120文字以内）の生成
- キーワード密度チェック（3〜5%）
- 内部リンクの挿入提案（既存記事からの関連リンク）
- `drafts/{slug}/meta.json` を生成

**meta.json の形式:**
```json
{
  "title": "Claude Codeとは？できることを完全解説【2026年最新版】",
  "slug": "claude-code-introduction",
  "meta_description": "Claude Codeの機能・使い方・料金を初心者向けに解説。...",
  "focus_keyword": "Claude Code",
  "categories": ["生成AI"],
  "tags": ["Claude Code", "AI", "プログラミング"],
  "yoast_seo": {
    "_yoast_wpseo_title": "%%title%% | %%sitename%%",
    "_yoast_wpseo_metadesc": "Claude Codeの機能・使い方...",
    "_yoast_wpseo_focuskw": "Claude Code"
  }
}
```

### 3.5 Agent: wp-publisher

**ファイル:** `.claude/agents/wp-publisher/wp-publisher.md`

```yaml
---
name: wp-publisher
description: "WordPress REST APIで画像アップロードと記事の下書き投稿を行う"
tools:
  - Read
  - Bash
  - Glob
model: haiku
permissionMode: acceptEdits
---
```

**役割:**
1. 画像を WordPress メディアライブラリにアップロード
2. 記事HTML内の画像プレースホルダーを実際のURLに置換
3. 下書き記事を投稿（featured_media にアイキャッチを設定）
4. Yoast SEOメタデータを設定
5. 結果（下書きURL）をユーザーに報告

**実行コマンド:**
```bash
python wp-auto-poster/lib/wp_client.py \
  --draft-dir drafts/{slug}/ \
  --action publish-draft
```

---

## 4. Python モジュール設計

### 4.1 lib/config.py

```python
"""環境変数の読み込みと設定管理"""
from dotenv import load_dotenv
import os

load_dotenv()

# WordPress
WP_URL = os.getenv("WP_URL", "https://m-totsu.com")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# 画像設定
EYECATCH_MODEL = "gemini-3-pro-image-preview"
EYECATCH_SIZE = "2K"
EYECATCH_ASPECT = "16:9"
ILLUSTRATION_MODEL = "gemini-2.5-flash-image"
ILLUSTRATION_ASPECT = "4:3"
```

### 4.2 lib/wp_client.py

**主要機能:**
- `upload_media(file_path, alt_text, title, caption)` → media_id を返す
- `create_draft(title, content, featured_media_id, meta, categories, tags)` → post_id, url を返す
- `publish_draft_from_dir(draft_dir)` → 画像アップロード + 下書き投稿の一括実行

**認証:** Basic認証（アプリケーションパスワード）
**エンドポイント:**
- `POST /wp-json/wp/v2/media` — 画像アップロード
- `POST /wp-json/wp/v2/posts` — 下書き投稿（status: "draft" 固定）

### 4.3 lib/image_client.py

**主要機能:**
- `generate_eyecatch(prompt, output_path)` → Nano Banana Pro（2K, 16:9）
- `generate_illustration(prompt, output_path)` → Nano Banana Flash（4:3）
- `generate_from_requests(requests_json, output_dir)` → 一括生成

**エラーハンドリング:**
- 指数バックオフによるリトライ（最大3回）
- レート制限時は自動待機
- 生成失敗時はプレースホルダー画像で代替

### 4.4 lib/mermaid_renderer.py

**主要機能:**
- `render(mermaid_code, output_path, width=1200, theme="default")` → PNG生成
- `render_from_requests(requests_json, output_dir)` → 一括生成

**依存:**
- `npx @mermaid-js/mermaid-cli`（Node.js）
- `mermaid-config.json`（日本語フォント設定）

---

## 5. 画像生成の使い分け

| 用途 | ツール | モデル/方式 | 解像度 | コスト/枚 | 理由 |
|------|--------|-----------|--------|----------|------|
| アイキャッチ | Gemini API | Nano Banana Pro | 2K (2048px) | $0.134（約20円） | 品質最優先、日本語テキスト対応 |
| 記事内挿絵 | Gemini API | Nano Banana Flash | 1K (1024px) | $0.039（約6円） | コスト効率、十分な品質 |
| 図解・ダイアグラム | Mermaid CLI | mmdc → PNG | 1200px | 無料 | 正確さ重視、テキスト確実 |

### 月間コスト試算

| 前提 | 数値 |
|------|------|
| 月間記事数 | 30本 |
| 1記事あたり | アイキャッチ1 + 挿絵2 + 図解1 |

| 項目 | 枚数/月 | 単価 | 月額 |
|------|--------|------|------|
| アイキャッチ（Pro 2K） | 30枚 | $0.134 | $4.02（約600円） |
| 挿絵（Flash） | 60枚 | $0.039 | $2.34（約350円） |
| 図解（Mermaid） | 30枚 | 無料 | $0 |
| **合計** | **120枚** | | **$6.36（約950円）** |

### 総コスト（v1 → v2比較）

| 項目 | v1（旧） | v2（新） |
|------|---------|---------|
| Claude API（記事生成） | 500〜1,500円 | 0円（Claude Code自身で生成） |
| Gemini API（画像生成） | なし | 約950円 |
| Mermaid（図解） | なし | 0円 |
| **月間合計** | **500〜1,500円** | **約950円** |

※ Claude Code のサブスクリプション費用（Max Plan等）は別途

---

## 6. データフロー詳細

### Step 1: ユーザーがSkillを呼び出す

```
/generate-post "Claude Codeとは？できることを完全解説"
```

### Step 2: 記事執筆Agent が起動（並列の1つ目）

```
入力: テーマ文字列
出力:
  - drafts/{slug}/article.html        ← 記事HTML（画像プレースホルダー付き）
  - drafts/{slug}/image_requests.json  ← 画像生成リクエスト
```

### Step 3: 画像生成Agent が起動（並列の2つ目、Step 2完了後）

```
入力: drafts/{slug}/image_requests.json
処理:
  1. eyecatch → python lib/image_client.py (Nano Banana Pro)
  2. illustrations → python lib/image_client.py (Nano Banana Flash)
  3. diagrams → python lib/mermaid_renderer.py (mmdc)
出力:
  - drafts/{slug}/images/*.png
  - drafts/{slug}/image_results.json
```

### Step 4: SEOレビューAgent（Step 2完了後）

```
入力: drafts/{slug}/article.html
処理: タイトル・メタ・キーワード・内部リンクの最適化
出力: drafts/{slug}/meta.json
```

### Step 5: 投稿Agent（Step 3, 4 完了後）

```
入力: article.html + images/ + meta.json + image_results.json
処理:
  1. 画像をWordPressメディアにアップロード → media_id取得
  2. article.html内のプレースホルダーを実URLに置換
  3. 下書き記事を投稿（featured_media設定、Yoast SEOメタ設定）
出力: 下書きURL（ユーザーに報告）
```

---

## 7. 実装フェーズ

### Phase 0: 環境構築（1日）

- [ ] Node.js確認（Mermaid CLIに必要）
- [ ] Python仮想環境構築
- [ ] `requirements.txt` 作成・インストール
  ```
  google-generativeai>=0.8.0
  requests>=2.31.0
  python-dotenv>=1.0.0
  python-slugify>=8.0.0
  Pillow>=10.0.0
  ```
- [ ] `.env` ファイル作成
  ```
  WP_URL=https://m-totsu.com
  WP_USER=your_username
  WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
  GOOGLE_API_KEY=your_google_api_key
  ```
- [ ] WordPress側: 専用ユーザー作成 + アプリケーションパスワード発行
- [ ] Google AI Studio でGemini APIキー取得
- [ ] Mermaid CLI動作確認: `npx @mermaid-js/mermaid-cli -V`

### Phase 1: Python モジュール実装（1〜2日）

- [ ] `lib/config.py` — 環境変数管理
- [ ] `lib/wp_client.py` — WordPress REST API クライアント
  - [ ] 接続テスト
  - [ ] メディアアップロード
  - [ ] 下書き投稿
  - [ ] Yoast SEOメタデータ設定
- [ ] `lib/image_client.py` — Gemini API 画像生成クライアント
  - [ ] Nano Banana Flash（挿絵）
  - [ ] Nano Banana Pro（アイキャッチ）
  - [ ] エラーハンドリング・リトライ
- [ ] `lib/mermaid_renderer.py` — Mermaid → PNG 変換
  - [ ] mermaid-config.json（日本語フォント）
  - [ ] 一時ファイル管理
- [ ] `templates/cocoon_blocks.py` — Gutenbergブロック生成ヘルパー
- [ ] テスト実行

### Phase 2: Skills & Agents 定義（1日）

- [ ] `.claude/skills/generate-post/SKILL.md` 作成
- [ ] `.claude/agents/wp-article-writer/wp-article-writer.md` 作成
- [ ] `.claude/agents/wp-image-generator/wp-image-generator.md` 作成
- [ ] `.claude/agents/wp-seo-reviewer/wp-seo-reviewer.md` 作成
- [ ] `.claude/agents/wp-publisher/wp-publisher.md` 作成
- [ ] `.claude/CLAUDE.md` にプロジェクト固有の設定を追記

### Phase 3: 統合テスト（1日）

- [ ] `/generate-post "テスト記事"` で全フロー実行
- [ ] 画像生成の品質確認
- [ ] WordPress下書きの表示確認（Cocoonテーマでの見た目）
- [ ] Yoast SEOメタデータの反映確認
- [ ] エラーケースのテスト（API障害、レート制限等）

### Phase 4: プロンプト調整・品質向上（継続的）

- [ ] 記事テンプレートの品質チューニング
- [ ] 画像プロンプトのスタイル統一
- [ ] 内部リンク戦略の組み込み
- [ ] SEOスコアの最適化

---

## 8. 日常のワークフロー（v2）

### 基本操作（1コマンド）

```bash
# Claude Codeを起動して:
/generate-post "Claude Codeとは？できることを完全解説"

# → Agent Team が自動で:
#   1. 記事を執筆（3,000〜5,000文字）
#   2. アイキャッチ画像を生成（Nano Banana Pro）
#   3. 挿絵2枚を生成（Nano Banana Flash）
#   4. 図解をMermaidで生成
#   5. SEOメタデータを最適化
#   6. WordPressに下書き投稿
#
# → 結果が報告される:
#   「下書き投稿が完了しました: https://m-totsu.com/?p=123」
#   「生成画像: アイキャッチ1枚 + 挿絵2枚 + 図解1枚」
```

### v1との比較

| 操作 | v1（旧） | v2（新） |
|------|---------|---------|
| 記事生成 | `python generate.py --topic "..."` | `/generate-post "..."` 1コマンド |
| 画像 | なし（手動作成） | 自動生成（Gemini + Mermaid） |
| SEOレビュー | 手動 | Agent が自動最適化 |
| 投稿 | `python publish.py slug` | Agent が自動投稿 |
| **合計ステップ** | **3ステップ + 手動画像作成** | **1コマンド** |

---

## 9. セキュリティ注意事項

- `.env` は**絶対にGit管理しない**（.gitignoreに必ず記載）
- ファイルパーミッション: `chmod 600 .env`
- 管理者ではなく「編集者」権限の専用ユーザーを使用
- Google API キーの利用上限を Google Cloud Console で設定
- wp_client.py は**常に `status: "draft"` 固定**（公開は必ず手動）
- アプリケーションパスワードは3〜6ヶ月ごとにローテーション
- 画像生成のSynthID（電子透かし）は自動付与されるためそのまま利用

---

## 10. 既知の制約と対策

| 制約 | 対策 |
|------|------|
| Agent Teams のパーミッション問題 | `permissionMode: acceptEdits` または独立Task方式 |
| サブエージェントのネスト不可 | Skill内でフラットにTaskを起動する設計 |
| Gemini APIのレート制限 | リクエスト間に1秒の待機 + 指数バックオフ |
| Nano Banana Proがプレビュー版 | GA後にモデルID更新が必要な可能性 |
| Mermaid CLIのNode.js依存 | npxで都度実行（グローバルインストール不要） |
| mermaid.inkの日本語フォント未対応 | ローカルmmdc方式を採用（日本語確実対応） |

---

## 11. 次のアクション

1. **この計画書（v2）を承認** → 実装フェーズへ進む
2. **Phase 0: 環境構築** から開始
   - WordPress専用ユーザー + アプリケーションパスワード発行
   - Google AI Studio でGemini APIキー取得
3. **Phase 1: Python モジュール実装**
   - Agent Teams で並列実装可能（wp_client / image_client / mermaid_renderer）
4. **Phase 2: Skills & Agents 定義**
5. **Phase 3: 統合テスト**
6. **Phase 4: 本番運用開始**（初月10本→段階的に30本/月へ）
