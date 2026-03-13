---
name: gemini-image
description: "Gemini（gemini.google.com）のブラウザUIを使って画像を生成・ダウンロードする。/gemini-image <テーマ> または /gemini-image <詳細プロンプト> で呼び出す。テーマが曖昧な場合は3〜5問のヒアリングを行い、Googleの画像生成ガイドラインに基づいた高品質プロンプトを構築する。generate-post/wp-image-generatorの代替として、WordPressの記事生成フローでも自動呼び出しされる。ブログ用アイキャッチ・挿絵生成、単体での画像生成どちらでも必ずこのスキルを使うこと。"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - mcp__Claude_in_Chrome__tabs_context_mcp
  - mcp__Claude_in_Chrome__tabs_create_mcp
  - mcp__Claude_in_Chrome__navigate
  - mcp__Claude_in_Chrome__find
  - mcp__Claude_in_Chrome__read_page
  - mcp__Claude_in_Chrome__computer
  - mcp__Claude_in_Chrome__form_input
  - mcp__Claude_in_Chrome__javascript_tool
  - mcp__Claude_in_Chrome__get_page_text
---

# Gemini画像生成スキル

gemini.google.comのブラウザUIを操作して画像を生成・ダウンロードする。
Google AI Proプランのブラウザ枠を活用してAPIコストを削減することが目的。

## 動作モードの判定

`$ARGUMENTS` を確認してモードを決定する：

- `リクエストファイル:` を含む → **ワークフローモード**（generate-postからの呼び出し）
- `--direct` を含む → **ダイレクトモード**（詳細プロンプト確定済み、ヒアリング不要）
- それ以外 → **ガイドモード**（曖昧なテーマ → ヒアリング → プロンプト生成）

---

## ワークフローモード

generate-postスキルから以下の形式で呼び出される：

```
画像を生成してください。
リクエストファイル: drafts/{slug}/image_requests.json
出力先: drafts/{slug}/images/
結果ファイル: drafts/{slug}/image_results.json
```

### 処理手順

1. **リクエストファイルを読み込む**
   `image_requests.json` の形式は以下の2パターンがある：

   **オブジェクト形式**（AI画像生成）:
   ```json
   {
     "eyecatch": { "prompt": "...", "style": "...", "alt": "..." },
     "illustrations": [{ "id": "...", "prompt": "...", "alt": "...", "caption": "..." }]
   }
   ```

   **配列形式**（mermaid/screenshot混在）:
   ```json
   [{ "id": "...", "type": "mermaid", "mermaid_code": "..." }, ...]
   ```

2. **AI生成対象を絞り込む**
   `prompt` フィールドを持つアイテムのみ処理する。
   `type: "mermaid"` および `type: "screenshot"` はスキップする。

3. **各画像を順次生成**（後述のGemini操作手順に従う）
   eyecatch → illustrations の順で処理する。

4. **image_results.jsonを書き込む**

   ```json
   {
     "eyecatch": { "path": "images/eyecatch.png", "alt": "..." },
     "illustrations": [
       { "id": "illust_1", "path": "images/illustration_1.png", "alt": "...", "caption": "..." }
     ]
   }
   ```

   mermaidやscreenshotのアイテムは `image_results.json` に含めない（別スキルが処理するため）。

---

## ガイドモード

ユーザーが曖昧なテーマを渡してきた場合（例：`/gemini-image "ブログ用の画像"`）、
まずヒアリングを通じて高品質なプロンプトを構築してから生成する。

### ヒアリング（3〜5問）

以下の質問を `AskUserQuestion` で一度にまとめて提示する（最大4問まで同時表示可能）：

**必須ヒアリング項目：**

1. **用途** - ブログヘッダー（アイキャッチ）？本文の挿絵？その他？
2. **スタイル** - 写真リアル / フラットイラスト / 水彩 / 油絵 / テクニカル図解 / その他
3. **色調・雰囲気** - 暖色系（温かい）/ 寒色系（クール・技術的）/ カラフル / モノクロ
4. **被写体の詳細補足** - テーマについて追加で伝えたいことがあれば（なければ「なし」）

5問目は必要に応じて追加：
- ブログ用ならアスペクト比（横長16:9 / 正方形 / 縦長）を聞く

### プロンプト構築（Googleガイドラインベース）

ヒアリング結果を以下の7要素フレームワークに当てはめて詳細プロンプトを英語で生成する：

| 要素 | 内容 | 例 |
|------|------|-----|
| **Subject** | 主題・被写体 | "Mount Fuji at sunset" |
| **Context** | 背景・環境・設定 | "aerial view, surrounded by clouds" |
| **Style** | 画風・媒体・技法 | "oil painting, impressionist style" |
| **Lighting** | 光の質と方向 | "golden hour lighting, warm backlight" |
| **Color** | カラーパレット・色調 | "warm orange and purple tones" |
| **Composition** | 構図・アングル | "wide angle, rule of thirds" |
| **Mood** | 雰囲気・感情 | "serene, majestic, peaceful" |

**重要：**
- プロンプトは英語で作成する（Geminiの画像生成は英語プロンプトの方が品質が高い）
- 日本語テキストを画像内に描画するよう指示しない（AI生成の文字は不安定）
- WordPress用ならアスペクト比を末尾に追加（例：`--ar 16:9` は不要、"landscape orientation, wide format" で表現）

構築したプロンプトをユーザーに提示して確認を取り、OKなら生成に進む。

---

## ダイレクトモード

`--direct` フラグが付いている場合、ヒアリングをスキップして即座に生成する。
プロンプトは `--direct` 以降のテキストをそのまま使用する。

---

## Gemini操作手順（共通）

### 1. ブラウザタブの準備

```
tabs_context_mcp() → 現在のタブ一覧を取得
tabs_create_mcp() → 新しいタブを作成（または既存タブを使用）
navigate(url="https://gemini.google.com/app", tabId=...) → 新しい会話を開始
```

毎回 `https://gemini.google.com/app` にアクセスして新しい会話を開始する。
前の会話の履歴が混入しないよう、必ず `/app` に直接ナビゲートする。

### 2. プロンプトの英語化（重要）

Geminiの画像生成品質は英語プロンプトの方が大幅に高い。
**ワークフローモード**では `image_requests.json` の `prompt` フィールドが日本語で書かれていることが多い。
送信前に必ず以下の7要素フレームワークに従って英語プロンプトに変換する：

| 要素 | 変換のヒント |
|------|-------------|
| Subject | 主題・被写体を具体的に |
| Style | 「フラットデザイン」→ "flat design illustration", 「写真リアル」→ "photorealistic" |
| Lighting | 明示されていなければ省略可 |
| Color | 色指定を英語で（例：「青・白・赤」→ "blue, white and red"） |
| Composition | 横長が必要なら "landscape orientation" を末尾に追加 |

### 3. プロンプト入力

ページロードを確認後（`read_page` でテキスト入力エリアが見えるまで待つ）：

```
find(query="chat input field or message input", tabId=...) → 入力フィールドを特定
computer(action="left_click", coordinate=[x, y], tabId=...) → クリックしてフォーカス
computer(action="type", text="{英語プロンプト}", tabId=...) → プロンプトを入力
computer(action="key", text="Return", tabId=...) → 送信
```

### 4. 画像生成の完了待機

生成には20〜60秒かかる。`computer(action="wait")` は20秒以上でタイムアウトするため、
代わりに `computer(action="wait", duration=10)` を繰り返してスクリーンショットで確認する。

```
computer(action="wait", duration=10, tabId=...) → 待機
computer(action="screenshot", tabId=...) → 画面確認
# まだ生成中なら再度待機して確認
```

生成完了のサイン：
- 「Constructing ...」「Evaluating ...」などの生成中テキストが消える
- 画像がチャット内に表示される
- 画像右上にダウンロードボタン（↓アイコン）が現れる

最大3分間（18回試行）待機。タイムアウトしたらスキップして次の画像へ。

### 5. 画像のダウンロード（プロジェクト内保存）

ダウンロードボタンで `~/Downloads/` に保存し、`mv` でプロジェクト内に移動する。
`mv ~/Downloads/...` は Claude Code の承認プロンプトなしで実行可能（実証済み）。

#### ステップA: 出力ディレクトリを準備 & ダウンロード前状態を記録

```bash
# ワークフローモード: 指定された出力先（例: drafts/{slug}/images/）
# ガイドモード / ダイレクトモード: カレントディレクトリ配下の gemini_images/
mkdir -p "{出力先ディレクトリ}"

# 新ファイル特定のため現在の最新ファイルを記録
BEFORE_LATEST=$(ls -t ~/Downloads/Gemini_Generated_Image_*.png 2>/dev/null | head -1)
```

#### ステップB: ダウンロードボタンをクリック

```
# 画像右上のダウンロードボタンをクリック
find(query="フルサイズの画像をダウンロード", tabId=...)
→ クリック

# 「フルサイズでダウンロードしています...」バナーが表示されるので待機
computer(action="wait", duration=5, tabId=...)
```

#### ステップC: 新ファイルを検出してプロジェクトに移動

```bash
# ダウンロード完了を待ち、最新ファイルを取得
sleep 3
LATEST=$(ls -t ~/Downloads/Gemini_Generated_Image_*.png 2>/dev/null | head -1)

# 新しいファイルであることを確認してから移動
if [ "$LATEST" != "$BEFORE_LATEST" ] || [ -z "$BEFORE_LATEST" ]; then
  mv "$LATEST" "{出力先ディレクトリ}/{ファイル名}.png"
  echo "✅ 保存完了: {出力先ディレクトリ}/{ファイル名}.png"
else
  echo "⚠️ 新しいファイルが見つかりません。ダウンロードを再試行してください。"
fi
```

### 6. ファイル名の決定

**ワークフローモード：**
- eyecatch → `eyecatch.png`
- illustrations[0] → `illustration_1.png`
- illustrations[1] → `illustration_2.png`
- （連番）

**ガイドモード / ダイレクトモード（単体使用）：**
- プロンプトの最初の40文字を英語スラッグ化してファイル名にする
- 例：`sunset_fuji_oil_painting_impressionist.png`
- 変換：小文字化 → スペース・記号をアンダースコアに → 40文字で切る
- デフォルト保存先は `{CWD}/gemini_images/`

```bash
# スラッグ化の例（Bash）
echo "A photorealistic image of Mount Fuji at sunset" | \
  tr '[:upper:]' '[:lower:]' | \
  tr -cs '[:alnum:]' '_' | \
  cut -c1-40
# → a_photorealistic_image_of_mount_fuji_at_
```

---

## エラーハンドリング

- **ログイン未済の場合**: スクリーンショットでログイン画面が見えたら「Geminiへのログインが必要です。ブラウザで gemini.google.com にログインしてから再試行してください。」と報告して停止する
- **生成タイムアウト**: 3分以上かかった場合はスキップして次の画像へ進む（ワークフローモード）。単体使用なら「タイムアウトしました。プロンプトを短くして再試行してください。」と報告する
- **ダウンロード失敗**: ダウンロードボタンが見つからない場合は、画像を右クリック→「名前を付けて画像を保存」を試みる
- **新ファイル未検出**: `sleep` を増やして再試行（大きな画像は10秒以上かかることがある）
- **Gemini応答エラー**: テキスト応答のみで画像が生成されなかった場合（コンテンツポリシー等）はスキップして次へ進む

---

## 完了報告

**ワークフローモード：**
```
✅ 画像生成完了
- アイキャッチ: images/eyecatch.png
- 挿絵1: images/illustration_1.png
- 挿絵2: images/illustration_2.png
```

**ガイドモード / ダイレクトモード：**
```
✅ 画像を保存しました: gemini_images/sunset_fuji_oil_painting.png
使用プロンプト: "A photorealistic sunset over Mount Fuji..."
```
