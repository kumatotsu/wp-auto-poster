---
name: git-push
description: "コード変更後に git add → commit → push を行う。/git-push または /git-push \"コミットメッセージ\" で呼び出す。引数なしの場合は変更内容からメッセージを自動生成する。"
allowed-tools:
  - Bash
  - Read
  - Glob
context: fork
---

# git commit & push スキル

コード変更後に必ず実行するスキル。変更内容を確認してコミットメッセージを自動生成し、
リモートリポジトリへプッシュする。

## ルール

**このプロジェクトでは、コードを変更したら必ず `/git-push` を実行すること。**

- コミット粒度: 論理的なまとまりで1コミット（複数ファイルでも機能単位であれば可）
- ブランチ: main に直接コミット（feature ブランチは不要）
- コミットメッセージ形式: `type: 内容（日本語可）`
  - `feat:` 新機能
  - `fix:` バグ修正
  - `docs:` ドキュメント更新
  - `chore:` 設定・依存関係の変更
  - `refactor:` リファクタリング

## 実行手順

### Step 1: リポジトリルートを特定

```bash
git -C /Users/totsu00/ClaudeCodeWork rev-parse --show-toplevel
```

### Step 2: 変更内容を確認

```bash
git -C /Users/totsu00/ClaudeCodeWork status
git -C /Users/totsu00/ClaudeCodeWork diff --stat
```

### Step 3: コミットメッセージを決定

- `$ARGUMENTS[0]` が指定されていればそれを使用
- 指定なしの場合は `git diff --stat` の内容から適切なメッセージを自動生成
  - 新規ファイルのみ → `feat: {ファイル名/機能名} を追加`
  - 既存ファイルの修正 → `fix:` または `feat:` を変更内容に基づいて判断
  - ドキュメントのみ → `docs: {内容} を更新`

### Step 4: ステージング・コミット・プッシュ

```bash
# 変更ファイルをステージ（.gitignore に従い除外される）
git -C /Users/totsu00/ClaudeCodeWork add -A

# コミット
git -C /Users/totsu00/ClaudeCodeWork commit -m "{コミットメッセージ}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# プッシュ
git -C /Users/totsu00/ClaudeCodeWork push origin main
```

### Step 5: 結果確認

```bash
git -C /Users/totsu00/ClaudeCodeWork log --oneline -3
```

コミットハッシュとコミットメッセージをユーザーに報告する。

## 注意事項

- `.env` ファイルは `.gitignore` により自動除外される（コミットしない）
- `drafts/` ディレクトリも自動除外（ブログ記事は非公開）
- コミット前に `git status` で除外されるべきファイルが含まれていないか確認する
- `.env` がステージされそうになった場合は **即座に中断** してユーザーに警告する
