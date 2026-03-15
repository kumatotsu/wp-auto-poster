---
name: generate-post
description: "WordPress記事を自動生成して下書き投稿する。/generate-post <テーマ> または /generate-post <アウトライン> で呼び出す。記事執筆・画像生成・SEO最適化・WordPress下書き投稿まで自動で行う。"
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

指定されたテーマまたはアウトラインに基づいて、ブログ記事の生成からWordPress下書き投稿までを自動で実行する。

## 入力モード

### テーマモード（デフォルト）
- `$ARGUMENTS[0]` = 記事テーマ（例: `Claude Codeの使い方`）
- 簡潔な文字列のみ。テーマが指定されていない場合はエラーを表示して終了する。

### アウトラインモード
- `$ARGUMENTS` = 構造化されたアウトライン文字列
- 以下のいずれかの特徴を含む場合、アウトラインモードとして扱う:
  - `| フォーカスKW |` などのMarkdownテーブル行
  - `**リード文**:` または `**記事構成案**:` のセクション見出し
  - `- H2:` で始まるH2構成リスト

アウトラインの想定フォーマット例:
```
{タイトル}
| 項目 | 内容 |
|------|------|
| フォーカスKW | {キーワード} |
| 関連KW | {関連キーワード群} |
| 検索意図 | {意図の説明} |
...
**リード文**: {リード文テキスト}
**記事構成案**:
- H2: {セクション1}
- H2: {セクション2}
...
**想定内部リンク先**: {リンク先情報}
```

## 実行手順

### Step 0: 準備・モード判定

1. `$ARGUMENTS` を取得し、モードを判定する
   - `| フォーカスKW |`、`**リード文**:`、`- H2:` のいずれかを含む → **アウトラインモード**
   - それ以外 → **テーマモード**

2. タイトル・スラッグを決定する
   - **テーマモード**: テーマ文字列をそのまま使用
   - **アウトラインモード**: アウトライン1行目のタイトル文字列を使用

3. 日付とslugを生成: `{YYYY-MM-DD}_{slugified_title}`
4. 作業ディレクトリを作成: `drafts/{slug}/` と `drafts/{slug}/images/`
5. TodoWriteでタスクリストを作成して進捗管理
6. **USE_CODEXフラグを設定する**
   - `$ARGUMENTS` に `--no-codex` が含まれる場合: テーマから `--no-codex` を除去し `USE_CODEX = false` として次のステップへ進む（AskUserQuestionは不要）
   - 含まれない場合: 以下の AskUserQuestion でモードを確認する

```
AskUserQuestion(
  questions=[{
    "question": "Codex を使ってリサーチとアウトライン設計を行いますか？",
    "options": [
      {"label": "Codex を使う", "description": "通常モード。Codexで4軸リサーチ＋SEOアウトライン設計を行う"},
      {"label": "Codex を使わない", "description": "Claude直接モード。Codexトークン上限時などに使用"},
      {"label": "その他"}
    ],
    "multiSelect": false
  }]
)
```

   - 「Codex を使う」→ `USE_CODEX = true`
   - 「Codex を使わない」→ `USE_CODEX = false`

### Step 1: リサーチ（WebSearch）

**テーマモード**: フルリサーチを実施する。
1. WebSearchで3〜5クエリを実行し、テーマに関する最新トレンド・よくある課題を収集する
2. 収集した情報を以下の観点で整理する:
   - テーマの主要トピック・キーワード
   - 読者が関心を持ちそうなポイント
   - 記事に盛り込むと効果的な具体的エピソードの方向性
3. リサーチで参照した出典を `drafts/{slug}/sources.json` に保存する:
   ```json
   [
     {
       "id": 1,
       "title": "参照した記事・ページのタイトル",
       "site": "サイト名・メディア名",
       "url": "https://...",
       "accessed": "YYYY-MM-DD"
     }
   ]
   ```
   URLが取得できなかった情報源は sources.json から除外する（出典のない内容は引用番号なしで執筆する）。

**テーマモード（USE_CODEX = false 時の強化版リサーチ）**:

`USE_CODEX = false` の場合は、codex-researcher が実施する4軸リサーチを Claude 自身が代わりに実施する。

1. 以下の4軸で各2〜3クエリ（合計8〜12クエリ）を WebSearch で実行する:
   - **最新トレンド軸**: 「{テーマ} 2025」「{テーマ} 最新」「{テーマ} 動向」
   - **方法・手順軸**: 「{テーマ} 方法」「{テーマ} やり方」「{テーマ} 手順」
   - **疑問・課題軸**: 「{テーマ} 問題」「{テーマ} できない」「{テーマ} 注意点」
   - **実績・数値軸**: 「{テーマ} 事例」「{テーマ} 効果」「{テーマ} データ」

2. URL確認済みのソースを `sources.json` に保存する（URLなし情報源は除外）

3. 以下の内容を `drafts/{slug}/research_summary.md` に保存する:

   ```markdown
   # リサーチサマリー

   ## テーマ
   {テーマ名}

   ## 使用した検索クエリ
   1. {クエリ1}
   2. {クエリ2}

   ## 主要トピック・キーワード
   - {トピック1}（最大10項目）

   ## 読者の主な疑問・関心
   - {疑問1}（最大5項目）

   ## 記事に盛り込むと効果的なポイント
   - {ポイント1}（最大5項目）

   ## 出典数
   {件数}件（sources.json参照）
   ```

**アウトラインモード**: KW補完リサーチを必ず実施する（省略・スキップ禁止）。

> ⚠️ **重要**: `sources.json` を空配列 `[]` で手動作成してはならない。必ず以下の手順でWebSearchを実行してから作成すること。

1. アウトラインの「フォーカスKW」と「関連KW」を抽出する
2. WebSearchで2〜3クエリを実行し、以下を収集する:
   - フォーカスKWに関する信頼性の高い記事・公式ドキュメント
   - 記事内の具体的な数値・事実の裏付けとなる情報源
   - 読者に役立つ補足情報
3. アウトラインの「検索意図」と照合して、不足トピックがあれば記録する
4. WebSearchで取得したURLを持つ情報源を `drafts/{slug}/sources.json` に保存する:
   - URLが確認できた情報源のみ記載する（URLなしは除外）
   - 最低1件以上の出典を収集すること
   - やむを得ず出典が0件の場合のみ空配列 `[]` を書き込む（その理由をコメントに残す）

### Step 1.5: Codex によるアウトライン設計 ＋ A/Bリサーチ（並行実行）

> **USE_CODEX = false の場合（`--no-codex` フラグまたは選択でCodexなしを選んだ場合）:**
> Codex タスクを起動せず、Claude 自身が `outline.md` を生成して Step 1.6 へ進む。
>
> `drafts/{slug}/research_summary.md` と `drafts/{slug}/sources.json` を読み込み、
> 以下のフォーマットで `drafts/{slug}/outline.md` を生成する:
>
> ```markdown
> # {タイトル案}
>
> | 項目 | 内容 |
> |------|------|
> | フォーカスKW | {メインキーワード} |
> | 関連KW | {関連KW群} |
> | 検索意図 | {検索意図1行} |
> | 対象読者 | ITエンジニア・AIツール関心層 |
> | 差別化ポイント | {競合との差別化ポイント} |
>
> **リード文の方向性**: ...
>
> **記事構成案**:
> - H2: ...
>   - H3: ...
> ...
> - H2: まとめ
>
> **想定内部リンク先**: {m-totsu.com の関連記事}
> ```
>
> 生成後、Step 1.6 へ進む（`sources_codex.json` / `research_summary_codex.md` は生成しない）。

---

**USE_CODEX = true の場合（通常モード）:**

リサーチ完了後、以下の2タスクを**同時に**起動する。

#### 1.5-A: Codex アウトライン設計（codex-outline-planner）

```
Task(
  subagent_type="codex-outline-planner",
  prompt="以下のテーマとリサーチ結果をもとに、SEO最適化されたアウトラインを設計してください。
    テーマ: {テーマ}
    作業ディレクトリ: drafts/{slug}/
    出力先: drafts/{slug}/outline.md

    【リサーチ結果サマリー】
    {Step 1 で収集した主要情報（トレンド・競合記事の傾向・読者の疑問点）}

    【出典情報】
    sources.json パス: drafts/{slug}/sources.json",
  description="Codexアウトライン設計"
)
```

#### 1.5-B: Codex リサーチャー（A/Bテスト用・codex-researcher）

> ⚠️ **A/Bテスト中**: 既存のStep 1インラインリサーチと比較するための並行実行。
> `sources.json` は上書きしない。出力は `sources_codex.json` と `research_summary_codex.md`。

```
Task(
  subagent_type="codex-researcher",
  prompt="以下のテーマでリサーチを実行してください。
    テーマ: {テーマ}
    作業ディレクトリ: drafts/{slug}/
    モード: {テーマモード or アウトラインモード}
    {アウトラインモードの場合: アウトライン情報を追記}

    出力先:
    - drafts/{slug}/sources_codex.json
    - drafts/{slug}/research_summary_codex.md",
  description="Codexリサーチャー（A/Bテスト）"
)
```

両タスクの完了を待つ。
- 1.5-A失敗: Step 1.6へ進む（フォールバック: Claude がアウトラインを自力で設計）
- 1.5-B失敗: A/Bテスト結果なしとして続行（メインフローに影響なし）

### Step 1.6: ユーザーエピソードの収集（AskUserQuestion）

リサーチ結果を踏まえて、ユーザーに記事に盛り込む個人的なエピソードを質問する。
ユーザーならではの実体験を記事に含めることで、オリジナリティと信頼性を高める。

**質問の組み立て方:**
- リサーチで把握したテーマの主要トピックを簡潔に提示する
  - アウトラインモードの場合はアウトラインの「検索意図」と「記事構成案」を参照する
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
    "question": "「{テーマまたはタイトル}」について記事を書きます。あなたならではのエピソードを盛り込みたいのですが、どのような体験がありますか？",
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

**アウトライン優先モード（Codex アウトライン生成成功時）:**

`drafts/{slug}/outline.md` が存在する場合は、その内容を読み込んでアウトラインモードで実行する。

```
Task(
  subagent_type="wp-article-writer",
  prompt="以下のアウトラインに従ってWordPress記事を執筆してください。
    アウトラインの構成・見出し・リード文・キーワードを忠実に反映してください。
    出力先: drafts/{slug}/
    記事HTML → drafts/{slug}/article.html
    画像リクエスト → drafts/{slug}/image_requests.json

    【アウトライン（Codex設計）】
    {outline.md の全文}

    【ユーザーエピソード】
    {エピソード}

    【引用・出典の指示】
    {sources.json の内容}
    （出典ルールは通常のアウトラインモードと同じ）",
  description="記事執筆（Codexアウトライン使用）"
)
```

`drafts/{slug}/outline.md` が存在しない場合（Codex 失敗時）は、以下のフォールバックモードで実行する。

**テーマモード（フォールバック）:**

`drafts/{slug}/sources.json` の内容を読み込み、プロンプトに含めて渡す。

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
    エピソード: {エピソード}

    【引用・出典の指示】
    以下の出典リストを活用して記事を執筆してください。
    {sources.json の内容（JSON文字列として貼り付け）}

    出典がある場合（sources配列が空でない場合）は、以下のルールに従ってください：
    - 各出典に基づいた記述・数値・事実の直後に「出典: <a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{site}</a>」を付与する（例: 〜とされています。出典: <a href=\"https://...\" target=\"_blank\" rel=\"noopener noreferrer\">gihyo.jp</a>）
    - 複数出典を同時に示す場合は「出典: <a>A</a>、<a>B</a>」または「（出典: <a>A</a>、<a>B</a>）」の形式にする
    - 引用は記事末尾のまとめセクションだけでなく、**本文中の各H2セクションに最低1箇所以上**配置すること
    - 同じ出典でも複数の関連箇所に重複して引用してよい
    - 記事末尾に以下の形式で「引用・出典」セクションを追加する（Gutenbergブロック形式）:
      <!-- wp:heading {\"level\":2} -->
      <h2 class=\"wp-block-heading\">引用・出典</h2>
      <!-- /wp:heading -->
      <!-- wp:list -->
      <ul class=\"wp-block-list\">
      <li><a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{site}: {title}</a></li>
      ...
      </ul>
      <!-- /wp:list -->

    出典リストが空（[]）の場合は引用リンク・引用・出典セクションは不要です。",
  description="記事執筆"
)
```

**アウトラインモード:**

`drafts/{slug}/sources.json` の内容を読み込み、プロンプトに含めて渡す。

```
Task(
  subagent_type="wp-article-writer",
  prompt="以下のアウトラインに従ってWordPress記事を執筆してください。
    アウトラインの構成・見出し・リード文・キーワードを忠実に反映してください。
    出力先: drafts/{slug}/
    記事HTML → drafts/{slug}/article.html
    画像リクエスト → drafts/{slug}/image_requests.json

    【アウトライン】
    {アウトライン全文}

    【ユーザーエピソード】
    以下のユーザー自身の体験談を記事に自然に盛り込んでください。
    導入文や体験セクションなど、読者の共感を得やすい箇所に配置してください。
    エピソード: {エピソード}

    【引用・出典の指示】
    以下の出典リストを活用して記事を執筆してください。
    {sources.json の内容（JSON文字列として貼り付け）}

    出典がある場合（sources配列が空でない場合）は、以下のルールに従ってください：
    - 各出典に基づいた記述・数値・事実の直後に「出典: <a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{site}</a>」を付与する（例: 〜とされています。出典: <a href=\"https://...\" target=\"_blank\" rel=\"noopener noreferrer\">gihyo.jp</a>）
    - 複数出典を同時に示す場合は「出典: <a>A</a>、<a>B</a>」または「（出典: <a>A</a>、<a>B</a>）」の形式にする
    - 引用は記事末尾のまとめセクションだけでなく、**本文中の各H2セクションに最低1箇所以上**配置すること
    - 同じ出典でも複数の関連箇所に重複して引用してよい
    - 記事末尾に以下の形式で「引用・出典」セクションを追加する（Gutenbergブロック形式）:
      <!-- wp:heading {\"level\":2} -->
      <h2 class=\"wp-block-heading\">引用・出典</h2>
      <!-- /wp:heading -->
      <!-- wp:list -->
      <ul class=\"wp-block-list\">
      <li><a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{site}: {title}</a></li>
      ...
      </ul>
      <!-- /wp:list -->

    出典リストが空（[]）の場合は引用リンク・引用・出典セクションは不要です（アウトラインモードで独自構成の場合など）。",
  description="記事執筆"
)
```

完了後に `article.html`、`image_requests.json`、`affiliate_requests.json` が生成されることを確認する。

### Step 3: 画像生成・SEOレビュー・アフィリエイトリンク生成

**画像生成はインラインで実行**し、SEOレビューとアフィリエイトリンク生成はTaskで並列実行する。

#### 3-1: SEOレビューとアフィリエイトリンク生成を起動（並列）

以下の2つのタスクをTaskツールで**同時に**起動する：

**SEOレビュータスク:**

- テーマモードの場合:
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

- アウトラインモードの場合（フォーカスKWと関連KWをアウトラインから抽出して渡す）:
```
Task(
  subagent_type="wp-seo-reviewer",
  prompt="記事のSEOを最適化してください。
    記事ファイル: drafts/{slug}/article.html
    テーマ: {タイトル}
    フォーカスキーワード: {アウトラインから抽出したフォーカスKW}
    関連キーワード: {アウトラインから抽出した関連KW}
    検索意図: {アウトラインから抽出した検索意図}
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

2つの完了を待つ。

#### 3-2: 画像生成をインラインで実行（gemini-imageスキル・ワークフローモード）

**gemini-imageはブラウザツールを必要とするためTask経由では実行できない。**
generate-postの実行コンテキスト内でgemini-imageスキルの手順をそのまま実行する。

```
画像を生成してください。
リクエストファイル: drafts/{slug}/image_requests.json
出力先: drafts/{slug}/images/
結果ファイル: drafts/{slug}/image_results.json
```

gemini-imageスキルのワークフローモード手順（image_requests.jsonの読み込み→英語プロンプト変換→Geminiブラウザ操作→画像保存→image_results.json書き込み）を実行する。

3-1と3-2が両方完了してから次のステップへ進む。

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
- 使用モード（テーマモード / アウトラインモード）
- 生成された画像の一覧（アイキャッチ、挿絵、図解）
- SEOスコア（タイトル文字数、メタディスクリプション文字数、キーワード密度）
- アフィリエイトリンク情報（挿入された書籍名、リンク数）
- **引用・出典情報**: `sources.json` の内容を読み込み、以下の形式で一覧表示する:
  - 出典あり: 「引用出典: {件数}件」として各出典を番号付きで列挙（タイトル・サイト名・URL・参照日）
  - 出典なし（空配列 or ファイルなし）: 「引用出典: なし（アウトライン構成 / 出典取得なし）」と表示
- 次のアクション:「WordPress管理画面で内容を確認し、問題なければ『公開』ボタンを押してください」
- **Gemini API 利用料**: https://aistudio.google.com/spend で今月の累計を確認できます。確認後は `python lib/usage_tracker.py --record <金額>` で記録してください（例: `--record 147`）
- **【A/Bテスト比較】** `sources_codex.json` が存在する場合、以下を比較表示する:
  - インラインリサーチ（既存）: `sources.json` の件数・サイト名一覧
  - codex-researcher: `sources_codex.json` の件数・サイト名一覧
  - `research_summary_codex.md` の「主要トピック・キーワード」を抜粋
  - 両者で重複しているURL・ユニークなURLの件数
  - 一言コメント: 「codex-researcherが既存より優れている点 / 劣っている点」を簡潔に評価

## エラーハンドリング

- 各Stepが失敗した場合、エラー内容をユーザーに報告し、リトライの提案を行う
- 画像生成が部分的に失敗した場合、成功した画像のみで投稿を進める
- WordPress接続エラーの場合、.env の設定確認を促す

## 注意事項

- 投稿は**常に下書き（draft）**として保存する。公開は人間が手動で行う。
- 画像プロンプトに日本語テキストの描画は含めない（AI画像の文字は不安定なため）
- 内部リンクは既存記事のカテゴリ・タグに基づいて提案する
- アウトラインモードでは、アウトラインの「想定内部リンク先」情報を wp-article-writer に渡し、記事内のリンク配置に活用する
