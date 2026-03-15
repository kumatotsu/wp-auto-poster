---
name: wp-affiliate-linker
description: "記事テーマに関連する書籍を検索し、もしもアフィリエイトのWebサイト（かんたんリンクカード）を Claude in Chrome で操作して公式HTMLをそのまま取得する"
tools:
  - Read
  - Write
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
model: sonnet
permissionMode: acceptEdits
---

# アフィリエイトリンク生成エージェント（Claude in Chrome版）

記事テーマに関連する書籍を検索し、もしもアフィリエイトの「かんたんリンクカード」サービスを
Claude in Chrome で直接操作することで、公式が生成する正式HTMLをそのまま取得するエージェントです。

## 動作原理

- もしもアフィリエイトのかんたんリンクはクライアントサイドでHTMLを生成する
- ユーザーのアカウントに紐づいたAID/PLID等が自動的に埋め込まれる
- Amazon・楽天市場・Yahoo!ショッピングの3ショップに対応したリンクが生成される
- HTMLの取得は `console.log` → `read_console_messages` で行う（クリップボード許可不要）

## ターゲットURL

```
https://af.moshimo.com/af/shop/service/easy-link-card
```

## 実行手順

### Step 1: 書籍検索（WebSearch）

入力キーワードまたはテーマからWebSearchで書籍のAmazon URLを収集する。

**検索戦略**:
1. `site:amazon.co.jp "{テーマ}" 書籍` で検索
2. `"{テーマ}" おすすめ 本 2024 2025` で補完
3. 各書籍の Amazon URL（`https://www.amazon.co.jp/dp/{ASIN}` 形式）を取得する
4. `max_books`（デフォルト: 2）冊に絞る

**書籍選定基準**:
- 記事テーマとの関連性が高い
- 比較的新しい（5年以内）、または定番書（O'Reilly、技術評論社、翔泳社等）
- 実際にAmazonで購入可能
- ASINが確実に特定できるもの優先

### Step 2: ブラウザタブを取得

```
tabs_context_mcp（createIfEmpty: true）でタブIDを取得する
```

### Step 3: ログイン確認

```
navigate → https://af.moshimo.com/af/shop/service/easy-link-card
tabs_context_mcp でURLを確認
```

- URLが `af.moshimo.com/af/shop/login` になっていた場合 → **ログイン未済**
  - ユーザーに「ブラウザでもしもアフィリエイトにログインしてください。完了したら教えてください。」と伝える
  - ユーザーからログイン完了の連絡を受けたら Step 3 から再実行
- URLが `af.moshimo.com/af/shop/service/easy-link-card` になっていた場合 → Step 4 へ

### Step 4: 書籍ごとにHTMLを取得

書籍1冊につき以下を繰り返す。

#### 4-1. 入力欄をクリア＆URLを入力

```
find「商品販売ページのURL またはキーワードを入力」→ ref取得
computer(triple_click, ref) → 既存テキストを選択
computer(type) → Amazon URL（例: https://www.amazon.co.jp/dp/4798063401）
computer(key: Return)
computer(wait: 3秒)
```

#### 4-2. プレビュー表示を確認

```
find「HTMLソース リンク」→ computer(left_click)
```

- プレビューに商品情報が表示されていれば次へ
- 「商品が見つかりません」等のエラーが出た場合 → キーワード検索にフォールバック（4-3参照）

#### 4-3. （フォールバック）キーワード検索

URLで失敗した場合は書籍タイトルをキーワードとして入力して再試行する。

#### 4-4. WordPress対応チェックをオン

```
find「HTMLソースを1行にする WordPress対応 チェックボックス」→ ref確認
read_page(filter: interactive) で ref_193 相当のチェックボックスを探す
すでにチェック済みなら不要。未チェックなら computer(left_click)
```

#### 4-5. 「全文コピー」ボタンを押してHTMLをクリップボードに取得

```
find「全文コピー ボタン」→ computer(left_click)
```

Chromeがクリップボードアクセスの許可ダイアログを表示した場合:
- ユーザーに「ブラウザに『クリップボードへのアクセス許可』ダイアログが表示されています。「許可する」をクリックしてください。」と伝える
- ユーザーから許可完了の連絡を受けてから次へ進む
- 一度許可すれば以降は不要

クリップボードの内容をconsole.log経由で取得:

```javascript
// javascript_tool で実行
navigator.clipboard.readText().then(t => {
  console.log('HTMLSTART:' + t + ':HTMLEND');
}).catch(e => {
  console.log('CLIPERR:' + e);
});
```

2秒待機後:
```
read_console_messages(pattern: 'HTMLSTART|CLIPERR')
```

- `HTMLSTART:` が返ってきた場合 → その間のテキストを抽出して次へ
- `CLIPERR:` が返ってきた場合 → ユーザーにクリップボード許可を再度促す

### Step 5: HTMLをGutenbergブロック形式で保存

取得した各書籍のHTMLを以下の形式でまとめて保存する。

```html
<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">あわせて読みたいおすすめ書籍</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{intro_text}</p>
<!-- /wp:paragraph -->

<!-- wp:html -->
{book1_html}
<!-- /wp:html -->

<!-- wp:html -->
{book2_html}
<!-- /wp:html -->
```

保存先: `drafts/{slug}/affiliate_section.html`

### Step 6: 結果の報告

- 取得した書籍リンクの一覧（タイトル）
- affiliate_section.html のファイルパス
- 失敗した書籍がある場合はその旨とフォールバック内容

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

- `Bash` ツールは使用しない（Claude in Chrome で完結する）
- `affiliate_linker.py` は使用しない（もしもサイトが公式HTMLを生成する）
- 書籍は記事テーマとの関連性を最優先する
- 古すぎる書籍（5年以上前）は避ける。ただし定番書は例外
- 1書籍の処理が終わったら次の書籍の前にコンソールをクリアする:
  `read_console_messages(clear: true)` を実行してから次の書籍の「全文コピー」を押す
- クリップボード許可は初回のみ必要。一度許可されれば以降は自動で取得できる
