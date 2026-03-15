# todo

## Claudeパーソナライズ設定とCLAUDE.md使い分け記事アウトライン作成

- [x] `sources.json` と公式ソースを確認し、検索意図と差別化軸を整理する
- [x] `outline.md` を指定フォーマットで作成する
- [x] 出力内容を確認し、Review に結果を追記する

## codex-researcher エージェント定義作成

- [x] 既存のエージェント定義と generate-post のリサーチ要件を確認する
- [x] codex-researcher.md のフロントマターと本文を仕様どおり作成する
- [x] 作成内容を確認し、レビュー結果を追記する

## wp-codex-outline-designer SKILL 改修

- [x] 対象 SKILL ファイルの実在パスを確認する
- [x] 現行内容を読み、3件の修正箇所を特定する
- [x] 1行目タイトル行ルールを「1行目は記事タイトル案を書く」に修正する
- [x] `wp-seo-review` を `wp-seo-reviewer` に修正する
- [x] 完了条件に FAQ 3件以上の要件を戻す
- [x] 差分を確認し、レビュー結果を追記する

## codex-researcher MCP 呼び出し化

- [x] 対象エージェント定義の現行 Step 1 とツール定義を確認する
- [x] `Bash` を `mcp__codex__codex` に置き換える
- [x] Step 1 の呼び出し文とパース手順を MCP レスポンス前提に更新する
- [x] Step 2 以降を維持したまま差分確認とレビュー追記を行う

## Claude エージェント定義の MCP 移行

- [x] `codex-researcher.md` と `codex-outline-planner.md` の現行定義を確認する
- [x] `codex-researcher.md` を Codex MCP による一括リサーチ委譲フローへ更新する
- [x] `codex-outline-planner.md` を Codex MCP の直接レスポンス受領フローへ更新する
- [x] 差分確認を行い Review に変更内容を追記する

## Claudeパーソナライズ設定とCLAUDE.md使い分けリサーチ

- [x] `wp-codex-researcher` と関連 reference を確認し、調査クエリを設計する
- [x] 4軸で一次情報と信頼できる補助情報を収集し、JSON形式へ整理する
- [x] `sources_codex.json` と `research_summary_codex.md` を生成し、内容を検証する

## Review

- `drafts/2026-03-15_claude-personalize-claude-md-guide/sources.json` と Anthropic 公式ドキュメントを確認し、Webアプリのパーソナライズ機能と Claude Code の `CLAUDE.md` を分けて説明する構成方針を整理
- 読者の主要疑問である「重複しないか」「どこに置くか」「何が優先されるか」に答える H2/H3 を中心に `outline.md` を新規作成
- `H2: まとめ`、コードサンプル要否、内部リンク候補、FAQ 3件以上を含む補足メモを満たすことを確認

- `.claude/agents/codex-researcher/codex-researcher.md` を新規作成し、指定フロントマター、引数定義、Step 1〜4、エラーハンドリング、注意事項を記述
- 内容確認で、`gpt-5.4` 指定、JSONL の `turn.completed` 抽出コード、フォールバック3クエリ、`sources_codex.json` / `research_summary_codex.md` の出力仕様を含むことを確認
- `/Users/totsu00/codex-porjects/wp-auto-poster/skills/wp-codex-outline-designer/SKILL.md` に指定の3修正を適用して保存
- 差分確認で、固定タイトル例の削除、`wp-seo-reviewer` への修正、FAQ 3件要件の追加を確認
- `.claude/agents/codex-researcher/codex-researcher.md` の `tools` から `Bash` を削除し、`mcp__codex__codex` を追加
- Step 1 を `mcp__codex__codex(prompt=..., sandbox="read-only")` 前提へ更新し、JSONL の `turn.completed` 抽出説明を JSON 配列抽出と `JSON.parse` 方針へ置換
- Step 2〜4 とフォールバック3クエリは維持し、エラーハンドリングの失敗条件だけを Codex MCP ツール表記へ更新
- `.claude/agents/codex-researcher/codex-researcher.md` の `tools` から `WebSearch` と `WebFetch` を削除し、Codex に `web_search=live` を含む一括 Web リサーチを依頼する Step 1 へ置換
- `codex-researcher.md` の Step 2 で JSON オブジェクトの検証と整形方針を定義し、`sources_codex.json` には `accessed` を追加し `summary` を除外して保存する仕様へ更新
- `codex-researcher.md` のフォールバックを、Codex 失敗または JSON パース不可時に `sources_codex.json` を空配列保存し、`research_summary_codex.md` に失敗理由を記録して終了する仕様へ更新
- `.claude/agents/codex-outline-planner/codex-outline-planner.md` の `tools` を `Read`, `Write`, `mcp__codex__codex` に更新し、Step 2 を `mcp__codex__codex(prompt="...", sandbox="read-only")` 呼び出しへ置換
- `codex-outline-planner.md` から Bash 経由の Codex CLI 呼び出し詳細と JSONL パース説明を削除し、Codex MCP ツール呼び出し失敗時の表現へ更新
- `wp-codex-researcher` と関連 reference を確認し、JSON返却専用Skillであることを踏まえて、今回依頼では追加で `sources_codex.json` と `research_summary_codex.md` を保存する方針を採用
- Claude Help Center と Claude Code Docs の一次情報を中心に、profile preferences、project instructions、styles、memory、`CLAUDE.md`、system prompt 差分を4軸で確認
- `drafts/2026-03-15_claude-personalize-claude-md-guide/sources_codex.json` を新規作成し、既存 `sources.json` を保持したまま確認日付きの出典一覧 6 件を保存
- `drafts/2026-03-15_claude-personalize-claude-md-guide/research_summary_codex.md` を新規作成し、検索クエリ、主要トピック、読者疑問、記事反映ポイント、出典数を要約
