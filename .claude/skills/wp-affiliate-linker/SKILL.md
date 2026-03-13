---
name: wp-affiliate-linker
description: "記事テーマまたは既存ドラフトに対してアフィリエイトリンクを生成する。/wp-affiliate-linker <テーマ> または /wp-affiliate-linker <slug> で呼び出す。書籍を検索し、もしもアフィリエイト「かんたんリンク」形式のHTMLを生成してWordPress記事に挿入できる形にする。generate-postとは独立して単体実行可能。アフィリエイトリンクを追加したい、書籍リンクを生成したい、という要求でも必ずこのスキルを使うこと。"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - WebSearch
  - WebFetch
context: fork
---

# アフィリエイトリンク生成スキル

記事テーマや既存ドラフトに対して書籍アフィリエイトリンクを生成する。単体でも generate-post フローの一部としても動作する。

## 入力モードの判定

`$ARGUMENTS` から動作モードを決定する：

- **テーマモード**（デフォルト）: `$ARGUMENTS` がテーマ文字列（例: `Claude Code 入門`）
  - 出力先: `/tmp/affiliate-{slug}/`（一時ディレクトリ）
- **ドラフトモード**: `$ARGUMENTS` が `drafts/` 以下のslugまたはパス（例: `2026-03-13_claude-code`）
  - 出力先: `drafts/{slug}/`（既存ドラフトに追記）

判定ルール: `drafts/` ディレクトリに同名ディレクトリが存在すればドラフトモード、なければテーマモード。

## Step 1: 準備

**テーマモード:**
1. テーマからslugを生成: 英数字とハイフンのみ、小文字（例: `claude-code-nyumon`）
2. 出力ディレクトリを作成: `mkdir -p /tmp/affiliate-{slug}`
3. `affiliate_requests.json` を生成:
   ```json
   {
     "keywords": ["{テーマ} 書籍", "{テーマ} 入門 本"],
     "context": "{テーマ}に関する記事向けの書籍アフィリエイト",
     "max_books": 2
   }
   ```
   → `/tmp/affiliate-{slug}/affiliate_requests.json` に保存

**ドラフトモード:**
1. `drafts/{slug}/affiliate_requests.json` を読み込む
2. なければテーマモードと同様に作成（テーマはslugから推測）

出力ディレクトリを変数 `{output_dir}` として以降使用する。

## Step 2: 書籍検索（WebSearch）

`affiliate_requests.json` の `keywords` と `context` を使って書籍を検索する。

各キーワードで以下を実行:
```
"{キーワード}" Amazon 書籍
"{キーワード}" おすすめ 技術書 2025
```

検索結果から抽出する情報:
- **書籍タイトル**: 正式名称
- **著者名**: 主要著者
- **ASIN**: Amazon商品ID（URLの `/dp/` 直後の10桁英数字）
- **Amazon URL**: `https://www.amazon.co.jp/dp/{ASIN}` 形式

ASINが見つかった場合、WebFetchで `https://www.amazon.co.jp/dp/{ASIN}` を確認してタイトルと出版社を正確に取得する。

## Step 3: 書籍選定

`max_books` 冊に絞る（デフォルト2冊）。選定基準:
- 記事テーマとの関連性が高い
- 比較的新しい（古すぎない。ただし定番書は例外）
- AmazonでASINが確認できる

## Step 4: affiliate_links.json の生成

```json
{
  "heading": "あわせて読みたいおすすめ書籍",
  "intro_text": "{テーマ}をさらに深めたい方には、以下の書籍がおすすめです。",
  "books": [
    {
      "title": "書籍タイトル [ 著者名 ]",
      "keyword": "書籍タイトル 著者名",
      "asin": "XXXXXXXXXX",
      "publisher": "出版社名",
      "image_url": "",
      "rakuten_url": ""
    }
  ]
}
```

→ `{output_dir}/affiliate_links.json` に保存

## Step 5: かんたんリンクHTML生成

```bash
cd /Users/totsu00/ClaudeCodeWork/wp-auto-poster
/Users/totsu00/.local/bin/uv run python lib/affiliate_linker.py \
  --request {output_dir}/affiliate_links.json \
  --output {output_dir}/affiliate_section.html
```

## Step 6: 結果報告

ユーザーに以下を報告する:
- 生成された書籍リスト（タイトル・ASIN）
- `affiliate_section.html` のパス
- **ドラフトモードの場合**: 「drafts/{slug}/affiliate_section.html に保存しました。WordPress投稿時に自動で記事末尾に挿入されます」と案内
- **テーマモード（単体実行）の場合**: HTMLの内容をチャットに表示してコピーできるようにする

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| 書籍が見つからない | 空のaffiliate_links.jsonを生成（booksが空配列） |
| ASINが特定できない | keywordのみで登録（検索リンクになる） |
| .env 設定なし | エラーを表示して停止 |

## 注意事項

- ASINが確実に特定できない場合は無理に入れない（keyword検索リンクで機能する）
- 5年以上前の書籍は避ける。ただし定番書（O'Reilly等）は例外
- 画像URLは空でよい（affiliate_linker.py がASINからGoogle Books APIで自動取得する）
