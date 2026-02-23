# Claude Code Skills & Agents 調査レポート

## 1. Skills（スキル）

### ディレクトリ構成

スキルは3つのレベルで定義可能：

```
# プロジェクト単位
.claude/skills/{skill-name}/SKILL.md

# 個人全体（全プロジェクト共通）
~/.claude/skills/{skill-name}/SKILL.md

# プラグイン
/plugin-dir/skills/{skill-name}/SKILL.md
```

### SKILL.md の構成

YAMLフロントマター + Markdown本文で構成。

```yaml
---
name: write-wp-post
description: "WordPressの記事を自動生成するスキル。/generate-post で呼び出し可能"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - Task
context: fork  # 分離されたサブエージェントで実行（推奨）
---

# WordPress記事生成スキル

以下の手順で記事を生成してください:
1. $ARGUMENTS からテーマを取得
2. ...
```

### 主要なフロントマターフィールド

| フィールド | 説明 | 例 |
|-----------|------|-----|
| `name` | スキル名（表示名） | `write-wp-post` |
| `description` | 説明（Claude の自動呼び出し判定に使用） | `"WordPress記事を生成する"` |
| `allowed-tools` | 許可するツールのリスト | `[Bash, Read, Write]` |
| `context` | 実行コンテキスト | `fork`（分離）/ なし（同一コンテキスト） |
| `disable-model-invocation` | Claudeの自動呼び出しを無効化 | `true` |
| `user-invocable` | ユーザーが `/skill-name` で呼べるか | `true`（デフォルト）/ `false` |
| `agent` | 使用するカスタムエージェント | `wordpress-writer` |

### 引数の受け渡し

```markdown
# ユーザーの呼び出し:
/generate-post "Claude Codeとは？完全解説" --category "入門"

# SKILL.md 内での参照:
$ARGUMENTS       → 全引数: "Claude Codeとは？完全解説" --category "入門"
$ARGUMENTS[0]    → 第1引数: "Claude Codeとは？完全解説"
$ARGUMENTS[1]    → 第2引数: --category
$0               → $ARGUMENTS[0] のショートカット
$1               → $ARGUMENTS[1] のショートカット
```

---

## 2. カスタムエージェント（.claude/agents/）

### ディレクトリ構成

```
# プロジェクト単位
.claude/agents/{agent-name}/{agent-name}.md

# 個人全体
~/.claude/agents/{agent-name}/{agent-name}.md
```

**重要**: ファイル名がディレクトリ名と一致する必要がある。

### エージェント定義ファイルの形式

YAMLフロントマター + Markdown本文（＝システムプロンプト）で構成。

```yaml
---
name: wordpress-writer
description: "WordPress向けのSEO最適化された記事を執筆するエージェント"
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - WebSearch
model: sonnet      # sonnet, opus, haiku, inherit（デフォルト）
permissionMode: acceptEdits  # default, acceptEdits, dontAsk, bypassPermissions, plan
skills:
  - write-wp-post  # プリロードするスキル
memory:
  - user           # ユーザーメモリ
  - project        # プロジェクトメモリ
---

# WordPress記事執筆エージェント

あなたはWordPress向けの技術ブログ記事を執筆する専門エージェントです。

## 役割
- Cocoonテーマに最適化されたHTMLで記事を生成
- Yoast SEO のスコア最大化を意識した構成
- 内部リンク構造を考慮した記事設計

## 出力形式
...
```

### 主要なフロントマターフィールド

| フィールド | 説明 | 値 |
|-----------|------|-----|
| `name` | エージェント識別子 | 小文字・ハイフン・数字のみ |
| `description` | 説明（Taskツールのdelegation判定に使用） | 文字列 |
| `tools` | 許可ツールリスト | ツール名の配列 |
| `model` | 使用モデル | `sonnet`, `opus`, `haiku`, `inherit` |
| `permissionMode` | 権限モード | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `skills` | プリロードするスキル | スキル名の配列 |
| `memory` | 永続メモリ設定 | `user`, `project`, `local` |
| `hooks` | ライフサイクルフック | オブジェクト |

### Taskツールからのサブエージェント呼び出し

カスタムエージェントは `subagent_type` にエージェント名を指定して呼び出せる：

```
Task(
    subagent_type="wordpress-writer",
    prompt="以下のテーマで記事を生成してください: Claude Codeとは？",
    description="記事生成"
)
```

---

## 3. Agent Teams

### TeamCreateの使い方

```
TeamCreate(
    team_name="wp-post-generation",
    description="WordPress記事生成チーム"
)
```

### チームメンバーの起動

```
Task(
    subagent_type="wordpress-writer",
    name="writer-agent",
    team_name="wp-post-generation",
    prompt="記事を書いてください"
)
```

### タスク管理

- TaskCreate: 新しいタスクを作成
- TaskList: タスク一覧を取得
- TaskUpdate: タスクのステータス・オーナーを更新
- SendMessage: チーム内メッセージング

### メッセージング

```
SendMessage(
    type="message",
    recipient="writer-agent",
    content="記事の生成が完了しました。SEOレビューをお願いします。",
    summary="記事生成完了通知"
)
```

---

## 4. WordPress自動投稿システムの実装構成

### 推奨アーキテクチャ

```
.claude/
├── skills/
│   └── generate-post/
│       └── SKILL.md           # メインのトリガースキル
├── agents/
│   ├── wp-article-writer/
│   │   └── wp-article-writer.md      # 記事執筆エージェント
│   ├── wp-image-generator/
│   │   └── wp-image-generator.md     # 画像生成エージェント
│   ├── wp-seo-reviewer/
│   │   └── wp-seo-reviewer.md        # SEOレビューエージェント
│   └── wp-publisher/
│       └── wp-publisher.md            # WordPress投稿エージェント
```

### Skill定義例: generate-post

```yaml
---
name: generate-post
description: "WordPress記事を自動生成して下書き投稿するスキル。/generate-post <テーマ> で呼び出す"
allowed-tools:
  - Task
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - TodoWrite
  - TeamCreate
  - SendMessage
context: fork
---

# WordPress記事自動生成

## 入力
$ARGUMENTS[0] = 記事テーマ

## 実行手順

1. Agent Team を作成して以下のエージェントを起動
2. 記事執筆エージェントが記事HTMLを生成
3. 画像生成エージェントがアイキャッチ・挿絵・図解を生成
4. SEOレビューエージェントがメタデータを最適化
5. 投稿エージェントがWordPressに下書き投稿

## 出力
- WordPress管理画面の下書きURL
- 生成された画像ファイル一覧
```

### Agent定義例: wp-article-writer

```yaml
---
name: wp-article-writer
description: "WordPress向けの技術ブログ記事を執筆する。Cocoon＋Yoast SEO最適化"
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
model: sonnet
permissionMode: acceptEdits
---

# WordPress記事執筆エージェント

あなたはWordPress（Cocoonテーマ）向けの技術ブログ記事を執筆する専門エージェントです。

## 記事の構成ルール
- H2は3〜5個
- H3は各H2の下に2〜3個
- 導入文は100〜200文字
- 各セクションにCocoon対応のHTMLブロックを使用

## SEO最適化
- タイトルは32文字以内
- メタディスクリプションは120文字以内
- 対象キーワードを自然に3〜5回含める

## 出力形式
drafts/{slug}/article.html に記事HTMLを保存
drafts/{slug}/meta.json にSEOメタデータを保存
```

---

## 5. 重要な制限と注意点

### Skills の制限
- 説明文がコンテキストに自動ロードされるため、多数のスキルがあるとコンテキスト消費が増加
- `disable-model-invocation: true` でClaudeの自動呼び出しを防止可能

### Agents の制限
- **サブエージェントのネストは不可**（サブエージェント内でさらにサブエージェント生成不可）
- CLAUDE.md は自動ロードされるが、会話履歴はロードされない
- タスク依存関係はAgent Teamsで管理

### チーム方式の制限（今回の実験で判明）
- チーム内エージェントのツールパーミッションが親と独立しているため、WebSearch等がブロックされる場合がある
- **対策**: 独立バックグラウンドタスクまたは `permissionMode: dontAsk` の設定が必要

---

## 6. 実装の優先順位

### Phase 1（基本）
- [ ] `.claude/skills/generate-post/SKILL.md` 作成
- [ ] `.claude/agents/wp-article-writer/wp-article-writer.md` 作成
- [ ] テスト呼び出し確認

### Phase 2（画像・SEO）
- [ ] `.claude/agents/wp-image-generator/wp-image-generator.md` 作成
- [ ] `.claude/agents/wp-seo-reviewer/wp-seo-reviewer.md` 作成
- [ ] Gemini API連携のPythonスクリプト

### Phase 3（統合・投稿）
- [ ] `.claude/agents/wp-publisher/wp-publisher.md` 作成
- [ ] WordPress REST API連携のPythonスクリプト
- [ ] エンドツーエンドテスト
