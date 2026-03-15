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
  - mcp__Claude_in_Chrome__navigate
  - mcp__Claude_in_Chrome__tabs_context_mcp
  - mcp__Claude_in_Chrome__tabs_create_mcp
  - mcp__Claude_in_Chrome__computer
  - mcp__Claude_in_Chrome__find
  - mcp__Claude_in_Chrome__read_page
  - mcp__Claude_in_Chrome__javascript_tool
  - mcp__Claude_in_Chrome__read_console_messages
  - mcp__Claude_in_Chrome__get_page_text
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

## Step 4: もしもアフィリエイト かんたんリンクカード でHTMLを取得

Claude in Chrome でもしもアフィリエイトのUIを操作し、公式生成HTMLをそのまま取得する。

### 4-1. タブを準備

```
tabs_context_mcp(createIfEmpty: true) でタブIDを取得
navigate → https://af.moshimo.com/af/shop/service/easy-link-card
```

### 4-2. ログイン確認

`tabs_context_mcp` でURLを確認:
- `login` を含む → ユーザーに「ブラウザでもしもアフィリエイトにログインしてください」と伝えて待機 → 完了連絡を受けたら再度 navigate
- `easy-link-card` → 次へ

### 4-3. 書籍ごとにHTMLを取得（各書籍を繰り返す）

**入力:**
```
find「商品販売ページのURL またはキーワードを入力」でテキストボックスを探す
computer(triple_click, ref) → computer(type) で Amazon URL を入力
  例: https://www.amazon.co.jp/dp/{ASIN}
computer(key: Return) → computer(wait: 3秒)
```

**HTMLソースセクションを開く:**
```
find「HTMLソース リンク」→ computer(left_click)
```

**WordPress対応チェック（未チェックなら）:**
```
find「HTMLソースを1行にする WordPress対応 チェックボックス」
→ チェックされていなければ computer(left_click)
```

**「全文コピー」ボタンでHTMLを取得:**
```
find「全文コピー ボタン」→ computer(left_click)
```

Chromeがクリップボード許可ダイアログを表示した場合:
- ユーザーに「ブラウザに『クリップボードへのアクセス許可』ダイアログが出ています。「許可する」をクリックしてください。」と伝えて待機
- 完了連絡を受けてから次へ（一度許可すれば以降は不要）

**クリップボード内容を読み取り:**
```javascript
// javascript_tool で実行
navigator.clipboard.readText().then(t => {
  console.log('HTMLSTART:' + t + ':HTMLEND');
}).catch(e => {
  console.log('CLIPERR:' + e);
});
```
```
computer(wait: 2秒)
read_console_messages(pattern: 'HTMLSTART|CLIPERR', clear: true)
```

- `HTMLSTART:～:HTMLEND` → 間のテキストをその書籍のHTMLとして保存
- `CLIPERR:` → ユーザーに再度許可を促す

**商品が見つからない場合のフォールバック:**
URLで失敗したら書籍タイトルをキーワードとして再試行する。それでも失敗したらその書籍をスキップ。

### 4-4. Gutenbergブロック形式で保存

取得した各書籍HTMLを以下の形式で結合して保存:

```html
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">あわせて読みたいおすすめ書籍</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{テーマ}をさらに深めたい方には、以下の書籍がおすすめです。</p>
<!-- /wp:paragraph -->

<!-- wp:html -->
{book1_html}
<!-- /wp:html -->

<!-- wp:html -->
{book2_html}
<!-- /wp:html -->
```

→ `{output_dir}/affiliate_section.html` に保存

## Step 5: 結果報告

ユーザーに以下を報告する:
- 生成された書籍リスト（タイトル・ASIN・ショップ数）
- `affiliate_section.html` のパス
- **ドラフトモードの場合**: 「drafts/{slug}/affiliate_section.html に保存しました。WordPress投稿時に自動で記事末尾に挿入されます」と案内
- **テーマモード（単体実行）の場合**: HTMLの内容をチャットに表示してコピーできるようにする

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| ログイン未済 | ユーザーにログインを促し待機 |
| 商品が見つからない（URL） | キーワード検索にフォールバック |
| 商品が見つからない（キーワード） | その書籍をスキップして続行 |
| クリップボード許可ダイアログ | ユーザーに「許可する」クリックを促して待機 |
| CLIPERR（許可拒否） | ユーザーに再度許可を促す |
| クリップボードが空 | 「全文コピー」ボタンを再クリックしてリトライ |

## 注意事項

- `affiliate_linker.py` は使用しない（もしもサイトが公式HTMLを生成する）
- もしもサイト経由で生成されるHTMLはAmazon・楽天市場・Yahoo!ショッピングの3ショップに対応している
- 5年以上前の書籍は避ける。ただし定番書（O'Reilly等）は例外
- ASINが確実に特定できない場合は書籍タイトルをキーワードとして入力する
