# Gemini API 画像生成 調査レポート

## 1. Nano Banana（Gemini 2.5 Flash Image）

### API仕様

| 項目 | 詳細 |
|------|------|
| モデルID | `gemini-2.5-flash-image` |
| 特徴 | 速度・効率性重視。コンテキスト理解力が高い |
| 出力解像度 | 最大1024x1024px |
| 出力形式 | Base64エンコードされたインラインデータ（PNG） |
| SynthID | 自動的に電子透かし付与 |
| アスペクト比 | `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` |

### Python SDKの使い方

```bash
pip install google-generativeai
```

```python
from google import genai

# クライアント初期化（APIキーは環境変数 GOOGLE_API_KEY から自動取得）
client = genai.Client()

# 基本的な画像生成
response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents="ブログのアイキャッチ画像: Claude Codeを使ったプログラミングのイラスト、モダンでクリーンなデザイン",
    config=genai.types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=genai.types.ImageConfig(
            aspect_ratio="16:9"  # ブログアイキャッチに最適
        )
    )
)

# 画像の保存
for part in response.parts:
    if part.inline_data:
        image = part.as_image()
        image.save("eyecatch.png")
        print(f"画像を保存しました: eyecatch.png")
```

### 料金

| 項目 | 料金 |
|------|------|
| 1画像あたり | $0.039（約6円） |
| バッチ処理 | $0.0195（約3円、50%割引） |
| 無料枠 | なし |
| 出力トークン | 1,290トークン/画像（$30/1Mトークン） |

---

## 2. Nano Banana Pro（Gemini 3 Pro Image）

### API仕様

| 項目 | 詳細 |
|------|------|
| モデルID | `gemini-3-pro-image-preview` |
| 特徴 | プロフェッショナル品質。日本語テキスト精度が高い |
| 出力解像度 | 1K（1024px）、2K（2048px）、4K（4096px） |
| 出力形式 | Base64エンコードされたインラインデータ（PNG） |
| SynthID | 自動的に電子透かし付与 |
| アスペクト比 | Nano Bananaと同様 |
| 画像サイズ指定 | `image_size` パラメータで `1K`, `2K`, `4K` を指定 |

### Python SDKの使い方

```python
from google import genai

client = genai.Client()

# Nano Banana Pro で高品質画像生成
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents="ブログのアイキャッチ: AIとプログラミングの融合をイメージした、洗練されたイラスト。青と白基調のモダンデザイン",
    config=genai.types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=genai.types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K"  # 高解像度
        )
    )
)

for part in response.parts:
    if part.inline_data:
        image = part.as_image()
        image.save("eyecatch_pro.png")
```

### 料金

| 解像度 | 通常料金 | バッチ処理 |
|--------|---------|-----------|
| 1K / 2K | $0.134/枚（約20円） | $0.067/枚（約10円） |
| 4K | $0.24/枚（約36円） | $0.12/枚（約18円） |

---

## 3. Nano Banana vs Nano Banana Pro 比較

| 項目 | Nano Banana | Nano Banana Pro |
|------|------------|----------------|
| モデルID | `gemini-2.5-flash-image` | `gemini-3-pro-image-preview` |
| 最大解像度 | 1024px | 4096px |
| 日本語テキスト | 可（品質はやや劣る） | 高精度（文字崩れ少ない） |
| 料金/枚 | $0.039（約6円） | $0.134（約20円）※2K |
| 生成速度 | 高速 | やや遅い |
| 用途 | 記事内挿絵、大量生成 | アイキャッチ、品質重視 |
| API利用 | 可能 | 可能（プレビュー版） |

---

## 4. 完全な実装コード例

### ブログ画像一括生成クラス

```python
import os
import time
from pathlib import Path
from google import genai

class BlogImageGenerator:
    """ブログ記事用の画像をGemini APIで生成するクラス"""

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Google API Key（省略時は環境変数 GOOGLE_API_KEY を使用）
        """
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()

    def generate_eyecatch(self, topic: str, output_path: str,
                          style: str = "モダンでクリーンなデザイン") -> str:
        """アイキャッチ画像を生成（Nano Banana Pro使用）"""
        prompt = (
            f"ブログ記事のアイキャッチ画像を生成してください。\n"
            f"テーマ: {topic}\n"
            f"スタイル: {style}\n"
            f"要件: テキストなし、16:9、ウェブ用の明るく魅力的な画像"
        )
        return self._generate(
            prompt=prompt,
            output_path=output_path,
            model="gemini-3-pro-image-preview",
            aspect_ratio="16:9",
            image_size="2K"
        )

    def generate_illustration(self, description: str, output_path: str) -> str:
        """記事内挿絵を生成（Nano Banana使用、コスト効率重視）"""
        prompt = (
            f"技術ブログの挿絵を生成してください。\n"
            f"内容: {description}\n"
            f"スタイル: シンプルでわかりやすいイラスト、フラットデザイン"
        )
        return self._generate(
            prompt=prompt,
            output_path=output_path,
            model="gemini-2.5-flash-image",
            aspect_ratio="4:3"
        )

    def _generate(self, prompt: str, output_path: str,
                  model: str, aspect_ratio: str,
                  image_size: str = None,
                  max_retries: int = 3) -> str:
        """画像生成の共通処理"""
        image_config_params = {"aspect_ratio": aspect_ratio}
        if image_size:
            image_config_params["image_size"] = image_size

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=genai.types.ImageConfig(**image_config_params)
                    )
                )

                # 画像パートを探して保存
                for part in response.parts:
                    if part.inline_data:
                        # 出力ディレクトリを作成
                        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                        image = part.as_image()
                        image.save(output_path)
                        return output_path

                raise RuntimeError("レスポンスに画像が含まれていません")

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数バックオフ
                    print(f"リトライ {attempt + 1}/{max_retries}: {e}")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"画像生成に失敗しました（{max_retries}回リトライ後）: {e}")

    def generate_blog_images(self, slug: str, topic: str,
                             illustrations: list[dict],
                             output_dir: str = "drafts") -> dict:
        """ブログ記事1本分の画像をまとめて生成"""
        base_dir = Path(output_dir) / slug / "images"
        results = {}

        # 1. アイキャッチ画像
        eyecatch_path = str(base_dir / "eyecatch.png")
        results["eyecatch"] = self.generate_eyecatch(topic, eyecatch_path)
        print(f"アイキャッチ生成完了: {eyecatch_path}")

        # 2. 挿絵
        results["illustrations"] = []
        for i, illust in enumerate(illustrations):
            illust_path = str(base_dir / f"illustration_{i+1}.png")
            self.generate_illustration(illust["description"], illust_path)
            results["illustrations"].append({
                "path": illust_path,
                "alt": illust.get("alt", f"挿絵{i+1}"),
                "caption": illust.get("caption", "")
            })
            print(f"挿絵{i+1}生成完了: {illust_path}")

            # レート制限対策: リクエスト間に短い待機
            time.sleep(1)

        return results


# 使用例
if __name__ == "__main__":
    generator = BlogImageGenerator()

    images = generator.generate_blog_images(
        slug="2026-02-21_claude-code-intro",
        topic="Claude Codeとは？できることを完全解説",
        illustrations=[
            {
                "description": "Claude Codeのターミナル画面でコードを生成している様子",
                "alt": "Claude Codeの操作画面",
                "caption": "Claude Codeでコードを自動生成している例"
            },
            {
                "description": "従来の手動コーディングとAIコーディングの比較図",
                "alt": "手動 vs AI コーディング",
                "caption": "AIコーディングで開発効率が大幅に向上"
            }
        ]
    )

    print(f"生成結果: {images}")
```

---

## 5. レート制限

| 項目 | Nano Banana | Nano Banana Pro |
|------|------------|----------------|
| RPM（リクエスト/分） | 未公開（推定10-30） | 未公開（推定5-15） |
| RPD（リクエスト/日） | 未公開 | 未公開 |
| バッチAPI | 利用可能（レート制限緩和） | 利用可能 |

**対策:**
- リクエスト間に `time.sleep(1)` を挿入
- 指数バックオフでリトライ
- 大量生成時はバッチAPIを活用（50%コスト削減も可能）

---

## 6. コスト試算

### 前提条件
- 月30記事
- 1記事あたり: アイキャッチ1枚（Pro 2K） + 挿絵2枚（Flash）

### 月間コスト

| 画像タイプ | モデル | 枚数/月 | 単価 | 月額 |
|-----------|--------|--------|------|------|
| アイキャッチ | Nano Banana Pro (2K) | 30枚 | $0.134 | $4.02（約600円） |
| 挿絵 | Nano Banana (Flash) | 60枚 | $0.039 | $2.34（約350円） |
| **合計** | | **90枚** | | **$6.36（約950円）** |

### バッチAPI利用時

| 画像タイプ | モデル | 枚数/月 | 単価 | 月額 |
|-----------|--------|--------|------|------|
| アイキャッチ | Nano Banana Pro (2K) | 30枚 | $0.067 | $2.01（約300円） |
| 挿絵 | Nano Banana (Flash) | 60枚 | $0.0195 | $1.17（約175円） |
| **合計** | | **90枚** | | **$3.18（約475円）** |

---

## 7. 画像プロンプト設計のベストプラクティス

### アイキャッチ画像のプロンプト構造

```
ブログ記事のアイキャッチ画像を生成してください。
テーマ: [記事テーマ]
スタイル: [デザインスタイル]
要件:
- テキストや文字は含めない
- ウェブ用の明るく魅力的な画像
- [ブランドカラー]基調
- プロフェッショナルな印象
```

### 挿絵のプロンプト構造

```
技術ブログの挿絵を生成してください。
内容: [具体的な説明]
スタイル: シンプルでわかりやすいイラスト
要件:
- フラットデザイン
- 明るい配色
- 概念を視覚的に表現
```

### プロンプトのコツ

1. **テキストは含めない指定を明示**: AI生成画像の文字はまだ不安定なため
2. **具体的な色調を指定**: ブランドの一貫性を保つ
3. **ネガティブプロンプト的な表現**: 「写実的すぎない」「暗くない」など
4. **アスペクト比を意識**: アイキャッチは16:9、挿絵は4:3が最適

---

## 8. 本プロジェクトでの推奨実装

### 使い分けまとめ

| 用途 | モデル | 理由 |
|------|--------|------|
| アイキャッチ | Nano Banana Pro (2K) | 品質最優先、日本語テキスト対応 |
| 記事内挿絵 | Nano Banana (Flash) | コスト効率、十分な品質 |
| 図解・ダイアグラム | Mermaid (mmdc) | 正確さ重視、テキスト確実 |

### 必要な環境変数

```bash
# .env に追加
GOOGLE_API_KEY=your_google_api_key_here
```

### 必要なライブラリ

```
google-generativeai>=0.8.0
Pillow>=10.0.0  # 画像処理（as_image()に必要）
```
