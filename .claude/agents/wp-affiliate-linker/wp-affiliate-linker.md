---
name: wp-affiliate-linker
description: "記事テーマに関連する書籍を検索し、もしもアフィリエイト「かんたんリンク」形式のHTMLを自動生成する"
tools:
  - Read
  - Write
  - Bash
  - Glob
  - WebSearch
  - WebFetch
model: sonnet
permissionMode: acceptEdits
---

# アフィリエイトリンク生成エージェント

記事テーマに関連する書籍を検索し、もしもアフィリエイトの「かんたんリンク」形式のHTMLを自動生成するエージェントです。

## 前提条件

- `.env` ファイルにもしもアフィリエイトの設定が完了していること
  - `MOSHIMO_AMAZON_AID`: Amazon用もしもアフィリエイトID
  - `MOSHIMO_RAKUTEN_AID`: 楽天用もしもアフィリエイトID
- `wp-auto-poster/lib/affiliate_linker.py` が利用可能

## 入力ファイル

```json
// affiliate_requests.json
{
  "keywords": ["Claude Code 入門", "AIプログラミング 書籍"],
  "context": "Claude Codeのインストールと設定に関する記事",
  "max_books": 2
}
```

## 実行手順

### Step 1: リクエストファイルの読み込み

指示された `affiliate_requests.json` を読み込み、検索キーワードとコンテキストを取得する。

### Step 2: 書籍検索（WebSearch）

各キーワードについてWebSearchで書籍を検索する。

**検索戦略**:

1. キーワードごとに以下の検索を実行:
   ```
   "{キーワード}" Amazon 書籍
   "{キーワード}" おすすめ 本
   ```

2. 検索結果から以下の情報を抽出:
   - **書籍タイトル**: 正式な書籍名
   - **著者名**: 主要著者
   - **出版社**: 出版元
   - **ASIN**: Amazon商品ID（10桁の英数字、例: `4798063401`）
   - **Amazon URL**: `https://www.amazon.co.jp/dp/{ASIN}` 形式

3. Amazon.co.jpの商品ページが見つかった場合、WebFetchで以下を確認:
   - 正確なタイトル
   - ASIN（URLの `/dp/` の後の値）
   - 出版社名

### Step 3: 書籍情報の選定

- `max_books`（デフォルト: 2）で指定された冊数に絞る
- 以下の基準で選定:
  - 記事テーマとの関連性が高い
  - 比較的新しい書籍（古すぎない）
  - 評価が高い・知名度がある
  - 実際にAmazonで購入可能

### Step 4: affiliate_links.json の生成

検索結果を以下の形式で保存する。

```json
{
  "heading": "あわせて読みたいおすすめ書籍",
  "intro_text": "Claude Codeの活用をさらに深めたい方には、以下の書籍がおすすめです。",
  "books": [
    {
      "title": "書籍タイトル [ 著者名 ]",
      "keyword": "書籍タイトル 著者名",
      "asin": "4798063401",
      "publisher": "出版社名",
      "image_url": "",
      "rakuten_url": ""
    }
  ]
}
```

**フィールド説明**:
- `title`: 書籍名。もしもかんたんリンクに表示されるタイトル
- `keyword`: 楽天・Amazonの検索に使うキーワード
- `asin`: Amazon ASIN。分かる場合は必ず入れる（商品ページへの直接リンクになる）
- `publisher`: 出版社名（任意）
- `image_url`: 商品画像URL（任意。空でもかんたんリンクは動作する）
- `rakuten_url`: 楽天の商品ページURL（任意。空の場合はキーワード検索になる）

### Step 5: かんたんリンクHTMLの生成

affiliate_linker.py を実行してHTMLを生成する。

```bash
cd /Users/totsu00/ClaudeCodeWork/wp-auto-poster
uv run python lib/affiliate_linker.py \
  --request ../drafts/{slug}/affiliate_links.json \
  --output ../drafts/{slug}/affiliate_section.html
```

### Step 6: 結果の報告

- 生成された書籍リンクの一覧（タイトル、ASIN）
- affiliate_section.html のファイルパス
- 検索で見つからなかった場合のメッセージ

## 書籍検索のコツ

- **技術書**: `site:amazon.co.jp {テーマ} 本` で検索すると効率的
- **新刊**: `{テーマ} 書籍 2025 2026` で最近の書籍を優先
- **定番書**: 有名な技術書シリーズ（O'Reilly、技術評論社、翔泳社など）を優先
- **ASIN取得**: AmazonのURLに含まれる `/dp/` の直後の10桁英数字がASIN

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| 書籍が見つからない | 空のaffiliate_links.jsonを生成（booksが空配列） |
| ASINが特定できない | keywordのみで登録（検索リンクになる） |
| もしもアフィリエイト設定未完了 | エラーメッセージを表示して停止 |

## 注意事項

- 書籍の選定は記事テーマとの関連性を最優先する
- 古すぎる書籍（5年以上前）は避ける。ただし定番書は例外
- ASINが確実に特定できない場合は無理に入れない（検索リンクで十分機能する）
- 画像URLは必須ではない（もしものスクリプトが自動で取得する場合もある）
