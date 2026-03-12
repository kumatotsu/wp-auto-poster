"""
ブログ用画像生成クライアント

Google Gemini API（Nano Banana / Nano Banana Pro）を使用して、
ブログ記事のアイキャッチ画像と記事内挿絵を生成する。

使用方法:
    # image_requests.json から一括生成
    python lib/image_client.py --request drafts/slug/image_requests.json --output drafts/slug/images/

    # APIキーの動作確認テスト
    python lib/image_client.py --test
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors

# プロジェクト内モジュールのインポートを可能にする
_lib_dir = Path(__file__).resolve().parent
if str(_lib_dir.parent) not in sys.path:
    sys.path.insert(0, str(_lib_dir.parent))

from lib import config  # noqa: E402
from lib.usage_tracker import UsageTracker  # noqa: E402

# ロガー設定
logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    """画像生成に失敗した際の例外"""
    pass


class BlogImageGenerator:
    """Google Gemini API を使ったブログ画像生成クライアント。

    アイキャッチ画像（Nano Banana Pro）と記事内挿絵（Nano Banana Flash）の
    2種類の画像生成に対応する。
    """

    # アイキャッチ用のプロンプト補足（品質・構図・ライティング指示）
    _EYECATCH_SUFFIX = (
        "テキストや文字は一切含めないでください。"
        "構図: 主題を中央に配置した安定したバランスの良い構図、適度な余白。"
        "ライティング: 自然光または柔らかいスタジオライトで立体感と奥行きを演出。"
        "品質: 高解像度、鮮明なディテール、プロフェッショナルな仕上がり。"
        "ウェブサムネイル向けに、ひと目で内容が伝わる魅力的なビジュアルにしてください。"
    )

    # 挿絵用のプロンプト補足（フラットデザイン・視認性指示）
    _ILLUSTRATION_SUFFIX = (
        "シンプルでわかりやすいフラットデザインイラストで描いてください。"
        "スタイル: クリーンなライン、明るく彩度の高い配色、余白を活かした構図。"
        "主題を中央に配置し、ブログ記事の説明用として視認性を最優先にしてください。"
        "テキストや文字は含めないでください。"
    )

    # リクエスト間のクールダウン（レート制限対策）
    _REQUEST_INTERVAL: float = 2.0

    def __init__(self, api_key: str = None):
        """Google Gemini API クライアントを初期化する。

        Args:
            api_key: Google API キー。省略時は config.GOOGLE_API_KEY を使用。

        Raises:
            ValueError: APIキーが設定されていない場合。
        """
        self._api_key = api_key or config.GOOGLE_API_KEY
        if not self._api_key:
            raise ValueError(
                "Google API キーが設定されていません。"
                "環境変数 GOOGLE_API_KEY を設定するか、"
                "コンストラクタに api_key を渡してください。"
            )
        self._client = genai.Client(api_key=self._api_key)
        self._tracker = UsageTracker()
        logger.info("BlogImageGenerator を初期化しました")

    # ──────────────────────────────────────────────
    # 公開メソッド
    # ──────────────────────────────────────────────

    def generate_eyecatch(
        self,
        prompt: str,
        output_path: str,
        style: str = "モダンでクリーンなデザイン",
    ) -> str:
        """アイキャッチ画像を生成する（Nano Banana Pro 使用）。

        Args:
            prompt: 画像生成プロンプト。
            output_path: 保存先ファイルパス。
            style: スタイル指定（プロンプトに付加される）。

        Returns:
            保存先の絶対パス文字列。
        """
        # プロンプトにスタイルと補足指示を付加
        full_prompt = f"{prompt}\nスタイル: {style}\n{self._EYECATCH_SUFFIX}"

        result = self._generate(
            prompt=full_prompt,
            output_path=output_path,
            model=config.EYECATCH_MODEL,
            aspect_ratio=config.EYECATCH_ASPECT,
            image_size=config.EYECATCH_SIZE,
        )
        self._tracker.record("eyecatch", config.EYECATCH_MODEL, config.EYECATCH_SIZE)
        return result

    def generate_illustration(self, prompt: str, output_path: str) -> str:
        """記事内挿絵を生成する（Nano Banana Flash 使用）。

        Args:
            prompt: 画像生成プロンプト。
            output_path: 保存先ファイルパス。

        Returns:
            保存先の絶対パス文字列。
        """
        # プロンプトに補足指示を付加
        full_prompt = f"{prompt}\n{self._ILLUSTRATION_SUFFIX}"

        result = self._generate(
            prompt=full_prompt,
            output_path=output_path,
            model=config.ILLUSTRATION_MODEL,
            aspect_ratio=config.ILLUSTRATION_ASPECT,
        )
        self._tracker.record("illustration", config.ILLUSTRATION_MODEL)
        return result

    def generate_from_requests(
        self, requests_path: str, output_dir: str
    ) -> dict:
        """image_requests.json を読み込み、全画像を一括生成する。

        月次予算を超過している場合は API 生成をスキップし、
        プロンプトのみを image_prompts_manual.md に出力する。

        Args:
            requests_path: image_requests.json のパス。
            output_dir: 画像出力先ディレクトリ。

        Returns:
            生成結果の辞書:
            {
                "eyecatch": {"path": "...", "alt": "..."},
                "illustrations": [...],
                "budget_skipped": True/False,  # 予算超過でスキップした場合 True
                "prompts_file": "..."           # プロンプト出力ファイルパス（スキップ時）
            }
        """
        requests_path = Path(requests_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # image_requests.json を読み込み
        with open(requests_path, "r", encoding="utf-8") as f:
            image_requests = json.load(f)

        # ── 予算チェック ──
        budget = self._tracker.check_budget()
        if budget["should_warn"]:
            logger.warning(
                f"Gemini API 予算警告: 今月 ${budget['total_cost_usd']:.4f} / "
                f"予算 ${budget['budget_usd']:.2f} "
                f"({budget['budget_used_pct']:.1f}%)"
            )
        if budget["should_skip"]:
            logger.error(
                f"Gemini API 予算超過: ${budget['total_cost_usd']:.4f} >= "
                f"${budget['budget_usd']:.2f}。API 生成をスキップします。"
            )
            prompts_file = self._write_prompts_only(
                image_requests=image_requests,
                output_dir=output_dir,
                budget_stats=budget,
            )
            return {
                "eyecatch": None,
                "illustrations": [],
                "budget_skipped": True,
                "prompts_file": str(prompts_file),
                "budget_stats": budget,
            }

        results = {"eyecatch": None, "illustrations": []}

        # ── アイキャッチ生成 ──
        eyecatch_req = image_requests.get("eyecatch")
        if eyecatch_req:
            eyecatch_path = output_dir / "eyecatch.png"
            style = eyecatch_req.get("style", "モダンでクリーンなデザイン")
            logger.info("アイキャッチ画像を生成中...")

            try:
                saved_path = self.generate_eyecatch(
                    prompt=eyecatch_req["prompt"],
                    output_path=str(eyecatch_path),
                    style=style,
                )
                # alt テキスト: リクエストに指定があればそれを使い、なければプロンプトから生成
                alt_text = eyecatch_req.get("alt", eyecatch_req["prompt"][:100])
                results["eyecatch"] = {
                    "path": str(Path(saved_path).relative_to(output_dir.parent)),
                    "alt": alt_text,
                }
                logger.info(f"アイキャッチ画像を保存しました: {saved_path}")
            except ImageGenerationError as e:
                logger.error(f"アイキャッチ画像の生成に失敗しました: {e}")
                raise

            # レート制限対策のクールダウン
            time.sleep(self._REQUEST_INTERVAL)

        # ── 挿絵を順次生成 ──
        illustrations = image_requests.get("illustrations", [])
        for i, illust_req in enumerate(illustrations):
            illust_id = illust_req.get("id", f"illust_{i + 1}")
            illust_filename = f"illustration_{i + 1}.png"
            illust_path = output_dir / illust_filename

            logger.info(f"挿絵 [{illust_id}] を生成中... ({i + 1}/{len(illustrations)})")

            try:
                saved_path = self.generate_illustration(
                    prompt=illust_req["prompt"],
                    output_path=str(illust_path),
                )
                results["illustrations"].append({
                    "id": illust_id,
                    "path": str(Path(saved_path).relative_to(output_dir.parent)),
                    "alt": illust_req.get("alt", illust_req["prompt"][:100]),
                    "caption": illust_req.get("caption", ""),
                })
                logger.info(f"挿絵 [{illust_id}] を保存しました: {saved_path}")
            except ImageGenerationError as e:
                logger.error(f"挿絵 [{illust_id}] の生成に失敗しました: {e}")
                raise

            # 最後の画像以外はクールダウンを挿入
            if i < len(illustrations) - 1:
                time.sleep(self._REQUEST_INTERVAL)

        # ── 結果を image_results.json として保存 ──
        results["budget_skipped"] = False
        results_path = output_dir.parent / "image_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"画像生成結果を保存しました: {results_path}")

        return results

    def _write_prompts_only(
        self,
        image_requests: dict,
        output_dir: Path,
        budget_stats: dict,
    ) -> Path:
        """予算超過時にプロンプトのみを Markdown ファイルに出力する。

        出力ファイルに Google AI Studio で使用できるプロンプトを記載し、
        ユーザーが手動で画像生成できるようにする。

        Returns:
            生成したファイルのパス。
        """
        lines = [
            "# 画像生成プロンプト（手動生成用）",
            "",
            "> **Gemini API 月次予算超過のため、自動生成をスキップしました。**",
            f"> 今月の累計コスト: **${budget_stats['total_cost_usd']:.4f}**"
            f" / 予算: ${budget_stats['budget_usd']:.2f}",
            ">",
            "> 以下のプロンプトを [Google AI Studio](https://aistudio.google.com/) に貼り付けて手動生成してください。",
            "> モデル: `gemini-3.1-flash-image-preview`（または `gemini-2.0-flash-exp`）",
            "",
        ]

        eyecatch = image_requests.get("eyecatch")
        if eyecatch:
            style = eyecatch.get("style", "モダンでクリーンなデザイン")
            lines += [
                "## アイキャッチ画像 → `images/eyecatch.png` として保存",
                f"- アスペクト比: **16:9**（横長）",
                f"- 保存先: `{output_dir}/eyecatch.png`",
                "",
                "```",
                f"{eyecatch['prompt']}",
                f"スタイル: {style}",
                "テキストや文字は一切含めないでください。ウェブ用の明るく魅力的な画像にしてください。",
                "```",
                "",
            ]

        illustrations = image_requests.get("illustrations", [])
        for i, illust in enumerate(illustrations):
            illust_id = illust.get("id", f"illust_{i + 1}")
            lines += [
                f"## 挿絵 {i + 1}（{illust_id}） → `images/illustration_{i + 1}.png` として保存",
                f"- アスペクト比: **4:3**",
                f"- 保存先: `{output_dir}/illustration_{i + 1}.png`",
                f"- alt テキスト: `{illust.get('alt', '')}`",
                "",
                "```",
                f"{illust['prompt']}",
                "シンプルでわかりやすいイラスト、フラットデザインで描いてください。テキストや文字は含めないでください。",
                "```",
                "",
            ]

        prompts_file = output_dir.parent / "image_prompts_manual.md"
        prompts_file.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"プロンプトファイルを出力しました: {prompts_file}")

        # image_results.json にも記録（パスは null）
        results = {
            "eyecatch": None,
            "illustrations": [],
            "budget_skipped": True,
            "prompts_file": str(prompts_file),
        }
        results_path = output_dir.parent / "image_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return prompts_file

    def generate_blog_images(
        self,
        slug: str,
        topic: str,
        illustrations: list[dict],
        output_dir: str = None,
    ) -> dict:
        """ブログ記事1本分の画像をまとめて生成する便利メソッド。

        generate_from_requests の簡易版。image_requests.json を経由せず、
        直接パラメータを渡して画像を生成する。

        Args:
            slug: 記事のスラッグ（ディレクトリ名に使用）。
            topic: 記事のトピック（アイキャッチ用プロンプトに使用）。
            illustrations: 挿絵リクエストのリスト。各要素は
                {"prompt": "...", "alt": "...", "caption": "..."} 形式。
            output_dir: 画像出力先。省略時は DRAFTS_DIR/slug/images/。

        Returns:
            generate_from_requests と同じ形式の結果辞書。
        """
        if output_dir is None:
            output_dir = str(config.DRAFTS_DIR / slug / "images")

        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # image_requests.json 相当のデータを組み立て
        image_requests = {
            "eyecatch": {
                "prompt": (
                    f"技術ブログ記事「{topic}」のアイキャッチ画像。"
                    f"{topic}の概念や魅力を視覚的に表現する。"
                    "広角ショット、中央配置の安定した構図。プロフェッショナルで印象的なビジュアル。"
                ),
                "style": "モダンでクリーンなデザイン、深みのある背景色と明るいアクセントカラー",
                "alt": topic,
            },
            "illustrations": [
                {
                    "id": illust.get("id", f"illust_{i + 1}"),
                    "prompt": illust["prompt"],
                    "alt": illust.get("alt", illust["prompt"][:100]),
                    "caption": illust.get("caption", ""),
                }
                for i, illust in enumerate(illustrations)
            ],
        }

        # 一時的に image_requests.json を書き出して generate_from_requests に委譲
        requests_path = output_dir_path.parent / "image_requests.json"
        with open(requests_path, "w", encoding="utf-8") as f:
            json.dump(image_requests, f, ensure_ascii=False, indent=2)

        return self.generate_from_requests(
            requests_path=str(requests_path),
            output_dir=output_dir,
        )

    # ──────────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────────

    def _generate(
        self,
        prompt: str,
        output_path: str,
        model: str,
        aspect_ratio: str,
        image_size: str = None,
        max_retries: int = 3,
    ) -> str:
        """画像生成の共通処理。指数バックオフでリトライする。

        Args:
            prompt: 画像生成プロンプト。
            output_path: 保存先ファイルパス。
            model: 使用するモデル名。
            aspect_ratio: アスペクト比（例: "16:9"）。
            image_size: 画像サイズ（Nano Banana Pro のみ）。
            max_retries: 最大リトライ回数。

        Returns:
            保存先の絶対パス文字列。

        Raises:
            ImageGenerationError: リトライを超えても生成に失敗した場合。
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ImageConfig の構築（image_size は Nano Banana Pro のみ設定）
        image_config_params = {"aspect_ratio": aspect_ratio}
        if image_size is not None:
            image_config_params["image_size"] = image_size

        gen_config = genai.types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=genai.types.ImageConfig(**image_config_params),
        )

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(
                    f"画像生成リクエスト送信 (試行 {attempt}/{max_retries}): "
                    f"model={model}, aspect={aspect_ratio}, size={image_size}"
                )

                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=gen_config,
                )

                # レスポンスから画像データを取得して保存
                if response.candidates and response.candidates[0].content:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            image = part.as_image()
                            image.save(str(output_path))
                            logger.info(f"画像を保存しました: {output_path}")
                            return str(output_path.resolve())

                # 画像がレスポンスに含まれなかった場合
                raise ImageGenerationError(
                    f"APIレスポンスに画像データが含まれていません。"
                    f"モデル: {model}, プロンプト先頭: {prompt[:80]}..."
                )

            except genai_errors.ClientError as e:
                # レート制限エラー（429）等のクライアントエラー: 長めに待機してリトライ
                last_error = e
                error_str = str(e).lower()
                if "429" in error_str or "rate" in error_str or "quota" in error_str:
                    wait_time = 10
                    logger.warning(
                        f"レート制限に到達しました (429)。"
                        f"{wait_time}秒待機してリトライします... "
                        f"(試行 {attempt}/{max_retries})"
                    )
                else:
                    wait_time = 2 ** (attempt - 1)
                    logger.warning(
                        f"クライアントエラー: {e}。"
                        f"{wait_time}秒後にリトライします... "
                        f"(試行 {attempt}/{max_retries})"
                    )
                if attempt < max_retries:
                    time.sleep(wait_time)

            except (genai_errors.ServerError, genai_errors.APIError) as e:
                # サーバーエラー / その他のAPIエラー: 指数バックオフでリトライ
                last_error = e
                wait_time = 2 ** (attempt - 1)  # 1秒, 2秒, 4秒
                logger.warning(
                    f"API エラーが発生しました: {e}。"
                    f"{wait_time}秒後にリトライします... "
                    f"(試行 {attempt}/{max_retries})"
                )
                if attempt < max_retries:
                    time.sleep(wait_time)

            except ImageGenerationError:
                # 画像データが含まれない場合もリトライ
                if attempt < max_retries:
                    wait_time = 2 ** (attempt - 1)
                    logger.warning(
                        f"画像データが取得できませんでした。"
                        f"{wait_time}秒後にリトライします... "
                        f"(試行 {attempt}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                # 予期しないエラー
                last_error = e
                logger.error(f"予期しないエラーが発生しました: {e}")
                if attempt < max_retries:
                    wait_time = 2 ** (attempt - 1)
                    time.sleep(wait_time)

        # 全リトライ失敗
        raise ImageGenerationError(
            f"画像生成に失敗しました（{max_retries}回リトライ済み）。"
            f"モデル: {model}, 最後のエラー: {last_error}"
        )


# ──────────────────────────────────────────────
# CLI インターフェース
# ──────────────────────────────────────────────

def _run_test():
    """APIキーの動作確認テスト。小さな画像を1枚生成して確認する。"""
    print("=" * 50)
    print("Gemini 画像生成 API テスト")
    print("=" * 50)

    # 設定バリデーション
    errors = config.validate_gemini_config()
    if errors:
        print(f"\n設定エラー:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print(f"\nAPI Key: {config.GOOGLE_API_KEY[:8]}...{config.GOOGLE_API_KEY[-4:]}")
    print(f"アイキャッチモデル: {config.EYECATCH_MODEL}")
    print(f"挿絵モデル: {config.ILLUSTRATION_MODEL}")

    try:
        generator = BlogImageGenerator()

        # テスト用の出力先
        test_dir = Path(config.DRAFTS_DIR) / "_test"
        test_dir.mkdir(parents=True, exist_ok=True)

        # 挿絵モデルで小さなテスト画像を生成（軽量なモデルを使用）
        test_path = test_dir / "test_image.png"
        print(f"\nテスト画像を生成中（{config.ILLUSTRATION_MODEL}）...")

        result = generator.generate_illustration(
            prompt="青空と緑の草原、シンプルな風景画",
            output_path=str(test_path),
        )

        print(f"\nテスト成功! 画像を保存しました: {result}")
        print(f"ファイルサイズ: {test_path.stat().st_size / 1024:.1f} KB")

    except ValueError as e:
        print(f"\n初期化エラー: {e}")
        sys.exit(1)
    except ImageGenerationError as e:
        print(f"\n画像生成エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n予期しないエラー: {e}")
        sys.exit(1)


def main():
    """CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(
        description="ブログ用画像生成クライアント（Gemini API）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # image_requests.json から一括生成
  python lib/image_client.py --request drafts/slug/image_requests.json --output drafts/slug/images/

  # APIキーの動作確認テスト
  python lib/image_client.py --test
        """,
    )

    parser.add_argument(
        "--request",
        type=str,
        help="image_requests.json のパス",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="画像出力先ディレクトリ",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="APIキーの動作確認テストを実行",
    )
    parser.add_argument(
        "--check-budget",
        action="store_true",
        help="今月の Gemini API 使用量・予算状況を表示して終了",
    )

    args = parser.parse_args()

    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 予算確認モード
    if args.check_budget:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_lib_dir / "usage_tracker.py")],
            capture_output=False,
        )
        sys.exit(result.returncode)

    # テストモード
    if args.test:
        _run_test()
        return

    # 一括生成モード
    if args.request and args.output:
        requests_path = Path(args.request)
        output_dir = Path(args.output)

        if not requests_path.exists():
            print(f"エラー: ファイルが見つかりません: {requests_path}")
            sys.exit(1)

        try:
            generator = BlogImageGenerator()
            results = generator.generate_from_requests(
                requests_path=str(requests_path),
                output_dir=str(output_dir),
            )
            print(f"\n画像生成が完了しました:")
            if results["eyecatch"]:
                print(f"  アイキャッチ: {results['eyecatch']['path']}")
            for illust in results["illustrations"]:
                print(f"  挿絵 [{illust['id']}]: {illust['path']}")

        except ValueError as e:
            print(f"初期化エラー: {e}")
            sys.exit(1)
        except ImageGenerationError as e:
            print(f"画像生成エラー: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"予期しないエラー: {e}")
            sys.exit(1)

        return

    # 引数不足
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
