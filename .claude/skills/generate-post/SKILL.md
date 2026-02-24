---
name: generate-post
description: "WordPress記事を自動生成して下書き投稿する。/generate-post <テーマ> で呼び出す。記事執筆・画像生成・SEO最適化・WordPress下書き投稿まで自動で行う。"
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
  - AskUserQuestion
context: fork
---

# WordPress記事自動生成スキル

指定されたテーマに基づいて、ブログ記事の生成からWordPress下書き投稿までを自動で実行する。

## 入力

- `$ARGUMENTS[0]` = 記事テーマ（必須）

テーマが指定されていない場合はエラーメッセージを表示して終了する。

## 実行手順

### Step 0: 準備

1. テーマを `$ARGUMENTS[0]` から取得
2. 日付とslugを生成: `{YYYY-MM-DD}_{slugified_theme}`
3. 作業ディレクトリを作成: `drafts/{slug}/` と `drafts/{slug}/images/`
4. TodoWriteでタスクリストを作成して進捗管理

### Step 1: テーマ調査（WebSearch）

記事テーマについて簡易リサーチを行い、テーマの全体像を把握する。

1. WebSearchで3〜5クエリを実行し、テーマに関する最新トレンド・話題・よくある課題を収集する
2. 収集した情報を以下の観点で整理する:
   - テーマの主要トピック・キーワード
   - 読者が関心を持ちそうなポイント
   - 記事に盛り込むと効果的な具体的エピソードの方向性

### Step 1.5: ユーザーエピソードの収集（AskUserQuestion）

リサーチ結果を踏まえて、ユーザーに記事に盛り込む個人的なエピソードを質問する。
ユーザーならではの実体験を記事に含めることで、オリジナリティと信頼性を高める。

**質問の組み立て方:**
- リサーチで把握したテーマの主要トピックを簡潔に提示する
- そのうえで「このテーマに関連する個人的なエピソードや体験談はありますか？」と尋ねる
- 質問はAskUserQuestionツールを使い、以下のような選択肢で具体的な方向性を示す:
  - 「導入のきっかけ・始めた理由」
  - 「使ってみて驚いた・困った体験」
  - 「成功体験・成果が出たエピソード」
  - （選択肢の内容はテーマに応じて調整する。ユーザーは「Other」で自由記述も可能）

**質問例:**

```
AskUserQuestion(
  questions=[{
    "question": "「{テーマ}」について調べたところ、{リサーチで分かった主要ポイント}が話題です。記事にあなたならではのエピソードを盛り込みたいのですが、どのような体験がありますか？",
    "header": "エピソード",
    "options": [
      {"label": "導入のきっかけ", "description": "使い始めた理由や背景のエピソード"},
      {"label": "驚き・困った体験", "description": "実際に使って予想外だったこと"},
      {"label": "成功体験・成果", "description": "うまくいった事例や具体的な成果"}
    ],
    "multiSelect": false
  }]
)
```

ユーザーの回答を `{エピソード}` として保持し、次のステップに引き継ぐ。

### Step 2: 記事執筆（Task → wp-article-writer）

Taskツールで `wp-article-writer` エージェントを起動する。
テーマに加えて、ユーザーから収集したエピソードも渡す。

```
Task(
  subagent_type="wp-article-writer",
  prompt="以下のテーマでWordPress記事を執筆してください。
    テーマ: {テーマ}
    出力先: drafts/{slug}/
    記事HTML → drafts/{slug}/article.html
    画像リクエスト → drafts/{slug}/image_requests.json

    【ユーザーエピソード】
    以下のユーザー自身の体験談を記事に自然に盛り込んでください。
    導入文や体験セクションなど、読者の共感を得やすい箇所に配置してください。
    エピソード: {エピソード}",
  description="記事執筆"
)
```

完了後に `article.html`、`image_requests.json`、`affiliate_requests.json` が生成されることを確認する。

### Step 3: 画像生成・SEOレビュー・アフィリエイトリンク生成（並列実行）

以下の3つのタスクをTaskツールで**同時に**起動する（1つのメッセージ内で3つのTask呼び出し）。

**画像生成タスク:**
```
Task(
  subagent_type="wp-image-generator",
  prompt="画像を生成してください。
    リクエストファイル: drafts/{slug}/image_requests.json
    出力先: drafts/{slug}/images/
    結果ファイル: drafts/{slug}/image_results.json",
  description="画像生成"
)
```

**SEOレビュータスク:**
```
Task(
  subagent_type="wp-seo-reviewer",
  prompt="記事のSEOを最適化してください。
    記事ファイル: drafts/{slug}/article.html
    テーマ: {テーマ}
    出力先: drafts/{slug}/meta.json",
  description="SEOレビュー"
)
```

**アフィリエイトリンク生成タスク:**
```
Task(
  subagent_type="wp-affiliate-linker",
  prompt="書籍のアフィリエイトリンクを生成してください。
    リクエストファイル: drafts/{slug}/affiliate_requests.json
    出力先: drafts/{slug}/
    結果ファイル: drafts/{slug}/affiliate_links.json
    HTMLファイル: drafts/{slug}/affiliate_section.html",
  description="アフィリエイトリンク生成"
)
```

3つすべての完了を待つ。

### Step 4: WordPress下書き投稿

画像とSEOメタデータが揃ったら、投稿タスクを起動する。

```
Task(
  subagent_type="wp-publisher",
  prompt="WordPressに下書き投稿してください。
    下書きディレクトリ: drafts/{slug}/
    コマンド: cd wp-auto-poster && uv run python lib/wp_client.py --action publish --draft-dir ../drafts/{slug}/",
  description="WordPress投稿"
)
```

### Step 5: 結果報告

ユーザーに以下を報告する:

- WordPress下書きURL
- 生成された画像の一覧（アイキャッチ、挿絵、図解）
- SEOスコア（タイトル文字数、メタディスクリプション文字数、キーワード密度）
- アフィリエイトリンク情報（挿入された書籍名、リンク数）
- 次のアクション:「WordPress管理画面で内容を確認し、問題なければ『公開』ボタンを押してください」

## エラーハンドリング

- 各Stepが失敗した場合、エラー内容をユーザーに報告し、リトライの提案を行う
- 画像生成が部分的に失敗した場合、成功した画像のみで投稿を進める
- WordPress接続エラーの場合、.env の設定確認を促す

## 注意事項

- 投稿は**常に下書き（draft）**として保存する。公開は人間が手動で行う。
- 画像プロンプトに日本語テキストの描画は含めない（AI画像の文字は不安定なため）
- 内部リンクは既存記事のカテゴリ・タグに基づいて提案する
