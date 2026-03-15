# SNS戦略 — Claude Code記事を中心とした多チャネル展開

作成日: 2026-03-15

---

## 戦略概要

「Claude Code を動画で学べる唯一のチャンネル（日本語）」を目指す。
WordPress ブログをコンテンツハブとし、SNS → Blog への流入と Blog → SNS での認知拡大を両立させる。

### 優先チャネル（順位）

| 順位 | チャネル | 役割 |
|------|---------|------|
| 1位 | **X（Twitter）** | リアルタイム認知・エンゲージメント・流入 |
| 2位 | **Zenn** | SEO流入・技術者コミュニティへの露出 |
| 3位 | **TikTok / YouTube Shorts** | 新規リーチ・ブランディング・動画SEO |

---

## 完全ワークフロー図

```
[Blog記事生成] /generate-post <テーマ>
       ↓
[WordPress 手動公開]  ← ここまで既存フロー
       ↓
【New】 /post-x          → X に要約ツイート投稿（Claude in Chrome）
       ↓
【New】 /post-zenn        → Zennに要約記事をgit push（手動公開）
       ↓
【New】 /notebooklm-add  → NotebookLM に公開URLをソース追加
                            → Video Overview → Brief（1〜3分）→ Cinematic スタイルで生成
       ↓
【New】 /generate-thumbnail → Gemini でマスコット入りサムネイル生成
       ↓
【New】 /upload-shorts    → YouTube Shorts / TikTok にアップロード（Claude in Chrome）
                            → 手動公開
```

---

## チャネル別戦略詳細

### 1位: X（Twitter）

**目的**: 即時認知・クリックスルー → Blog

**投稿フォーマット**:
- 記事公開直後に要約スレッド（3〜5ツイート）
- 1ツイート目: フック（「〇〇できる？」「〇〇の落とし穴」形式）
- 2〜4ツイート目: 記事の核心3点を箇条書き
- 最終ツイート: Blog URL + CTA（「全文はこちら↓」）
- ハッシュタグ: `#ClaudeCode` `#AI活用` `#Claude`

**自動化**: Claude in Chrome でX.comに投稿（`/post-x` スキル）

**KPI**: インプレッション数・クリック率・フォロワー増加数

---

### 2位: Zenn

**目的**: 技術者への露出・Blog への誘導

**投稿フォーマット**:
- Blog記事の要約版（800〜1500字）
- 冒頭に「この記事はXXXの要約です。詳細はこちら→[Blog URL]」
- Markdownで完結する内容にとどめ、詳細はBlogへ誘導
- タグ: `Claude` `ClaudeCode` `AI` `自動化` など

**自動化方針**: GitHub連携（git push → Zenn自動反映）
→ `/post-zenn` スキルが `drafts/{slug}/zenn_article.md` を生成してgit push
→ Zenn管理画面で手動公開（Claude in Chromeで開くだけ）

**KPI**: いいね数・バッジ数・被リンク数・Blog誘導クリック数

---

### 3位: TikTok / YouTube Shorts

**目的**: 新規リーチ・ビジュアルブランディング・動画SEO

**コンセプト**: マスコットキャラクター（女性）の授業スタイル

**動画制作ワークフロー**:
1. NotebookLM にブログ記事URLをソース追加
2. Studio → Video Overview → Brief（1〜3分）→ Cinematic スタイルで生成
3. 日本語対応済み
4. Gemini でマスコット入りサムネイル生成（`/generate-thumbnail`）
5. Claude in Chrome で YouTube Shorts / TikTok にアップロード
6. 手動公開

**投稿頻度目標**: 週2〜3本（Blog記事1本 → 動画1本）

**KPI**: 再生数・チャンネル登録者数・動画経由のBlog流入数

---

## スキル開発ロードマップ

| 優先 | スキル名 | 自動化内容 | 難易度 | 依存 |
|------|---------|-----------|--------|------|
| 1 | `/post-x` | Blog公開後にX要約スレッド投稿 | 低 | Claude in Chrome |
| 2 | `/post-zenn` | Zenn用MD生成 → git push | 低 | 既存git-pushの拡張 |
| 3 | `/generate-thumbnail` | マスコット入りサムネイル生成 | 低 | 既存gemini-imageの応用 |
| 4 | `/notebooklm-add` | URLソース追加 + Video生成トリガー | 中 | Claude in Chrome |
| 5 | `/upload-shorts` | YT Shorts / TikTok アップロード | 中〜高 | Claude in Chrome |

---

## `/post-x` スキル仕様

**入力**: `slug`（または公開済みBlog URL）
**処理**:
1. `drafts/{slug}/article.html` または WP APIから記事本文を取得
2. 要約スレッドを生成（フック + 3ポイント + URL）
3. Claude in Chrome で x.com/compose にアクセス
4. スレッド投稿

**注意**: 画像（アイキャッチ）を1枚目ツイートに添付すると効果的

---

## `/post-zenn` スキル仕様

**入力**: `slug`
**処理**:
1. `drafts/{slug}/article.html` から Zenn用Markdown（800〜1500字）を生成
2. Blog URL誘導文を冒頭に追加
3. `zenn-content/articles/{slug}.md` として保存
4. `git add → commit → push`（zenn-contentリポジトリ）

**前提**: Zenn の GitHub連携リポジトリが別途必要

---

## `/notebooklm-add` スキル仕様

**入力**: Blog公開URL
**処理**:
1. Claude in Chrome で notebooklm.google.com を開く
2. 対象ノートブックにURLをソースとして追加
3. Studio → Video Overview → Brief → Cinematic を選択して生成開始
4. 生成完了を待機（10〜15分）→ ダウンロード

---

## `/generate-thumbnail` スキル仕様

**入力**: `slug` または タイトルテキスト
**処理**:
1. 記事タイトルとマスコットキャラクター仕様をGeminiプロンプトに組み込む
2. Claude in Chrome で gemini.google.com にアクセス
3. サムネイル用画像（16:9 または 9:16）を生成・ダウンロード
4. `drafts/{slug}/images/thumbnail.png` に保存

---

## `/upload-shorts` スキル仕様

**入力**: `slug`（動画ファイルとサムネイルが drafts/{slug}/ に存在すること）
**処理**:
1. Claude in Chrome で YouTube Studio を開く
2. 動画ファイルをアップロード
3. タイトル・説明文・サムネイルを設定
4. 「Shorts」として設定（60秒以内 or #Shorts タグ）
5. 手動公開用に保存
6. TikTok も同様に操作

---

## コンテンツカレンダー（週次）

| 曜日 | アクション |
|------|-----------|
| 月 | Blog記事生成・投稿（/generate-post） |
| 月 | X要約スレッド投稿（/post-x） |
| 火 | Zenn要約記事 git push → 手動公開 |
| 水 | NotebookLM Video生成開始（/notebooklm-add） |
| 木 | サムネイル生成（/generate-thumbnail） |
| 金 | YouTube Shorts / TikTok アップロード（/upload-shorts）→ 手動公開 |

---

## 技術構成メモ

- **Claude in Chrome**: 全ブラウザ操作の基盤
- **GitHub連携**: Zenn投稿の安定化
- **NotebookLM Cinematic Video Overview**: Brief（1〜3分）で日本語動画生成
- **Gemini**: サムネイル・アイキャッチ生成（既存スキルの応用）
- **FFmpeg**: 必要に応じて音声+静止画のMP4合成（Bashで自動化可）

---

## 将来的な拡張候補

- **note（有料記事）**: プレミアムコンテンツの有料化・マネタイズ
- **Instagram Reels**: YouTube Shorts と同素材を流用
- **LINE公式アカウント**: 記事更新通知の自動配信
