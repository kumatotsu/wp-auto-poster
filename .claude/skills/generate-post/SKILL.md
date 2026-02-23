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

### Step 1: 記事執筆（Task → wp-article-writer）

Taskツールで `wp-article-writer` エージェントを起動する。

```
Task(
  subagent_type="wp-article-writer",
  prompt="以下のテーマでWordPress記事を執筆してください。
    テーマ: {テーマ}
    出力先: drafts/{slug}/
    記事HTML → drafts/{slug}/article.html
    画像リクエスト → drafts/{slug}/image_requests.json",
  description="記事執筆"
)
```

完了後に `article.html` と `image_requests.json` が生成されることを確認する。

### Step 2: 画像生成とSEOレビュー（並列実行）

以下の2つのタスクをTaskツールで**同時に**起動する（1つのメッセージ内で2つのTask呼び出し）。

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

両方の完了を待つ。

### Step 3: WordPress下書き投稿

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

### Step 4: 結果報告

ユーザーに以下を報告する:

- WordPress下書きURL
- 生成された画像の一覧（アイキャッチ、挿絵、図解）
- SEOスコア（タイトル文字数、メタディスクリプション文字数、キーワード密度）
- 次のアクション:「WordPress管理画面で内容を確認し、問題なければ『公開』ボタンを押してください」

## エラーハンドリング

- 各Stepが失敗した場合、エラー内容をユーザーに報告し、リトライの提案を行う
- 画像生成が部分的に失敗した場合、成功した画像のみで投稿を進める
- WordPress接続エラーの場合、.env の設定確認を促す

## 注意事項

- 投稿は**常に下書き（draft）**として保存する。公開は人間が手動で行う。
- 画像プロンプトに日本語テキストの描画は含めない（AI画像の文字は不安定なため）
- 内部リンクは既存記事のカテゴリ・タグに基づいて提案する
