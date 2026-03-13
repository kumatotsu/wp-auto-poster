---
name: update-post
description: "既存のWordPress下書き記事をdraftsディレクトリの内容で更新する。/update-post <post_id> <slug> で呼び出す。既存記事の修正・加筆・再投稿に使う。記事を更新したい、投稿を修正したい、post_idを指定して再投稿したい、という要求でも必ずこのスキルを使うこと。"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
context: fork
---

# WordPress記事更新スキル

既存のWordPress下書き記事を `drafts/{slug}/` ディレクトリの内容で上書き更新する。

## 引数

```
$ARGUMENTS[0] = post_id  （必須）WordPressの記事ID
$ARGUMENTS[1] = slug     （任意）draftsディレクトリのslug名
```

## Step 1: 引数の確認・slug特定

`post_id` が未指定の場合はエラーを表示して終了:
```
エラー: post_id を指定してください
使い方: /update-post <post_id> [slug]
例: /update-post 123 2026-03-13_claude-code
```

`slug` が指定されていない場合は `drafts/` 以下のディレクトリ一覧を表示してユーザーに選択させる:
```bash
ls -lt /Users/totsu00/ClaudeCodeWork/drafts/ | head -10
```

## Step 2: ドラフトディレクトリの確認

`drafts/{slug}/` に必要なファイルが揃っているか確認する:

```bash
ls /Users/totsu00/ClaudeCodeWork/drafts/{slug}/
```

必須: `article.html`
任意: `meta.json`（SEOメタ）、`image_results.json`（アップロード済み画像）、`affiliate_section.html`（アフィリエイト）

`article.html` がなければエラーを表示して終了。

## Step 3: 記事更新の実行

```bash
cd /Users/totsu00/ClaudeCodeWork/wp-auto-poster
/Users/totsu00/.local/bin/uv run python lib/wp_client.py \
  --action update \
  --post-id {post_id} \
  --draft-dir ../drafts/{slug}/
```

このコマンドは以下を自動で行う:
- `article.html` の本文を更新
- `meta.json` があればSEOメタ（タイトル・ディスクリプション）を更新
- `image_results.json` があればアイキャッチ画像を更新（再アップロードなし）
- `affiliate_section.html` があれば記事末尾に追記

## Step 4: 結果報告

成功時:
- 更新された記事のWordPress編集URL
- 更新内容の概要（本文・メタ・画像・アフィリエイトの有無）
- 「WordPress管理画面で内容を確認し、問題なければ『公開』ボタンを押してください」

失敗時:
- エラーメッセージを表示
- `wp-auto-poster/.env` の設定確認を促す

## 注意事項

- 投稿ステータスは変更しない（下書きは下書きのまま）
- 公開済み記事に対して実行した場合も内容のみ更新される（ステータスは公開のまま）
- 画像は `image_results.json` に記録済みのものを再利用（再アップロードしない）
