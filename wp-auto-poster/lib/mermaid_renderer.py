"""
Mermaid図解をPNG画像にレンダリングするモジュール

ローカルの mmdc (mermaid-cli) を優先して使用し、
利用不可の場合は mermaid.ink Web API にフォールバックする。
"""

import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

# プロジェクト内モジュールのインポートを可能にする
_lib_dir = Path(__file__).resolve().parent
if str(_lib_dir.parent) not in sys.path:
    sys.path.insert(0, str(_lib_dir.parent))

from lib import config  # noqa: E402

logger = logging.getLogger(__name__)

# mermaid.ink API のベースURL
MERMAID_INK_BASE = "https://mermaid.ink"


class MermaidRenderer:
    """Mermaid図解をPNG画像に変換するレンダラー

    ローカルの mmdc を優先し、利用不可なら mermaid.ink API にフォールバックする。
    """

    def __init__(self, config_path: str = None, prefer_api: bool = False):
        """Mermaidレンダラーを初期化。

        Args:
            config_path: mermaid-config.json のパス。
                         省略時は config.MERMAID_CONFIG を使用。
            prefer_api: True の場合、ローカルCLIよりもmermaid.ink APIを優先する。
        """
        if config_path is not None:
            self.config_path = Path(config_path)
        else:
            self.config_path = config.MERMAID_CONFIG

        # 設定ファイルの存在確認
        if self.config_path and not self.config_path.exists():
            logger.warning("Mermaid設定ファイルが見つかりません: %s", self.config_path)
            self.config_path = None

        self.prefer_api = prefer_api
        self._cli_available = None  # 遅延チェック

    # ──────────────────────────────────────────────
    # ローカル CLI (mmdc) 方式
    # ──────────────────────────────────────────────

    def check_cli_availability(self) -> bool:
        """npx 経由で mermaid-cli が利用可能か確認する。"""
        try:
            result = subprocess.run(
                ["npx", "@mermaid-js/mermaid-cli", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info("mermaid-cli バージョン: %s", version)
                return True
            else:
                logger.warning("mermaid-cli の確認に失敗: %s", result.stderr.strip())
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("mermaid-cli が利用できません（npx未検出またはタイムアウト）")
            return False

    def _render_cli(
        self,
        mermaid_code: str,
        output_path: Path,
        width: int,
        height: int,
        theme: str = None,
        background: str = "white",
    ) -> str:
        """ローカル mmdc で PNG に変換する。"""
        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".mmd", delete=False, encoding="utf-8"
            )
            tmp_file.write(mermaid_code)
            tmp_file.close()

            cmd = [
                "npx", "@mermaid-js/mermaid-cli",
                "-i", tmp_file.name,
                "-o", str(output_path),
                "-w", str(width),
                "-H", str(height),
                "-b", background,
            ]

            if theme:
                cmd.extend(["-t", theme])
            if self.config_path:
                cmd.extend(["-c", str(self.config_path)])

            logger.info("Mermaid CLI 変換: %s", " ".join(cmd))

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"mmdc エラー: {error_msg}")

            if not output_path.exists():
                raise RuntimeError(f"出力ファイルが見つかりません: {output_path}")

            return str(output_path.resolve())

        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

    # ──────────────────────────────────────────────
    # mermaid.ink Web API 方式
    # ──────────────────────────────────────────────

    def _render_api(
        self,
        mermaid_code: str,
        output_path: Path,
        theme: str = "default",
        background: str = "white",
    ) -> str:
        """mermaid.ink Web API で PNG に変換する。

        mermaid.ink の URL 形式:
        https://mermaid.ink/img/{base64_encoded_json}
        """
        # mermaid.ink が受け付ける JSON 形式
        graph_def = {
            "code": mermaid_code,
            "mermaid": {
                "theme": theme or "default",
            },
        }

        encoded = base64.urlsafe_b64encode(
            json.dumps(graph_def).encode("utf-8")
        ).decode("ascii")

        url = f"{MERMAID_INK_BASE}/img/{encoded}"
        logger.info("mermaid.ink API 変換: %s...", url[:100])

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Content-Typeの確認
        content_type = response.headers.get("content-type", "")
        if "image" not in content_type and len(response.content) < 100:
            raise RuntimeError(
                f"mermaid.ink がエラーを返しました: {response.text[:200]}"
            )

        with open(output_path, "wb") as f:
            f.write(response.content)

        logger.info("mermaid.ink で画像を生成しました: %s", output_path)
        return str(output_path.resolve())

    # ──────────────────────────────────────────────
    # 統合レンダリング（自動フォールバック）
    # ──────────────────────────────────────────────

    def render(
        self,
        mermaid_code: str,
        output_path: str,
        width: int = 1200,
        height: int = 800,
        theme: str = None,
        background: str = "white",
    ) -> str:
        """MermaidコードをPNG画像に変換する。

        ローカルCLIを試し、失敗した場合はmermaid.ink APIにフォールバックする。

        Args:
            mermaid_code: Mermaid記法のダイアグラムコード
            output_path: 出力PNG画像のパス
            width: 画像の幅（CLIモードのみ有効）
            height: 画像の高さ（CLIモードのみ有効）
            theme: テーマ名
            background: 背景色

        Returns:
            出力ファイルの絶対パス

        Raises:
            RuntimeError: CLI・API 両方とも失敗した場合
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        methods = []
        if self.prefer_api:
            methods = [("mermaid.ink API", self._try_api), ("ローカル CLI", self._try_cli)]
        else:
            methods = [("ローカル CLI", self._try_cli), ("mermaid.ink API", self._try_api)]

        last_error = None
        for method_name, method_func in methods:
            try:
                result = method_func(
                    mermaid_code, output_path, width, height, theme, background
                )
                logger.info("Mermaid図解を生成しました (%s): %s", method_name, output_path)
                return result
            except Exception as e:
                logger.warning("%s で失敗: %s", method_name, e)
                last_error = e
                continue

        raise RuntimeError(
            f"Mermaid変換が全ての方式で失敗しました。最後のエラー: {last_error}"
        )

    def _try_cli(self, mermaid_code, output_path, width, height, theme, background):
        """CLIでの変換を試みる"""
        return self._render_cli(mermaid_code, output_path, width, height, theme, background)

    def _try_api(self, mermaid_code, output_path, width, height, theme, background):
        """APIでの変換を試みる"""
        return self._render_api(mermaid_code, output_path, theme, background)

    # ──────────────────────────────────────────────
    # 一括変換
    # ──────────────────────────────────────────────

    def render_from_requests(
        self, requests_path: str, output_dir: str
    ) -> list[dict]:
        """image_requests.json の diagrams セクションからMermaid図解を一括生成する。

        Args:
            requests_path: image_requests.json のパス
            output_dir: 画像出力先ディレクトリ

        Returns:
            生成結果のリスト
        """
        requests_path = Path(requests_path)
        output_dir = Path(output_dir)

        if not requests_path.exists():
            raise FileNotFoundError(
                f"リクエストファイルが見つかりません: {requests_path}"
            )

        with open(requests_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        diagrams = data.get("diagrams", [])
        if not diagrams:
            logger.warning("diagrams セクションが空です: %s", requests_path)
            return []

        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for diagram in diagrams:
            diagram_id = diagram.get("id", "unknown")
            mermaid_code = diagram.get("mermaid_code", "")
            alt = diagram.get("alt", "")
            caption = diagram.get("caption", "")

            if not mermaid_code:
                logger.warning("diagram %s: mermaid_code が空のためスキップ", diagram_id)
                continue

            output_path = output_dir / f"{diagram_id}.png"

            try:
                rendered_path = self.render(
                    mermaid_code=mermaid_code,
                    output_path=str(output_path),
                )
                results.append({
                    "id": diagram_id,
                    "path": rendered_path,
                    "alt": alt,
                    "caption": caption,
                })
                logger.info("diagram %s: 生成成功 -> %s", diagram_id, rendered_path)
            except RuntimeError as e:
                logger.error("diagram %s: 生成失敗 - %s", diagram_id, e)

        logger.info("一括生成完了: %d/%d 件成功", len(results), len(diagrams))
        return results


# ──────────────────────────────────────────────
# CLIインターフェース
# ──────────────────────────────────────────────

def _run_test():
    """テストモード: サンプルフローチャートを生成して動作確認する。"""
    sample_code = """\
flowchart TD
    A[Claude Code] --> B[記事生成]
    B --> C[画像生成]
    C --> D[WordPress投稿]
"""
    output_path = Path(config.DRAFTS_DIR) / "test_mermaid.png"

    # API優先でテスト（ローカルCLIが使えない環境でも動作するように）
    renderer = MermaidRenderer(prefer_api=True)

    print("=== Mermaid レンダラー 動作確認テスト ===")
    print()

    # 1. ローカルCLIチェック
    print("[1/3] mermaid-cli (ローカル) の利用可能性を確認中...")
    cli_ok = renderer.check_cli_availability()
    if cli_ok:
        print("  OK: mermaid-cli は利用可能です。")
    else:
        print("  INFO: mermaid-cli は利用不可（mermaid.ink APIにフォールバック）")
    print()

    # 2. mermaid.ink APIチェック
    print("[2/3] mermaid.ink API の疎通確認中...")
    try:
        r = requests.get(f"{MERMAID_INK_BASE}/healthcheck", timeout=10)
        print(f"  OK: mermaid.ink は応答しています (status={r.status_code})")
    except Exception as e:
        print(f"  WARNING: mermaid.ink への接続に問題: {e}")
    print()

    # 3. サンプル図の生成
    print(f"[3/3] サンプルフローチャートを生成中 -> {output_path}")
    try:
        result_path = renderer.render(
            mermaid_code=sample_code,
            output_path=str(output_path),
        )
        file_size = os.path.getsize(result_path)
        print(f"  OK: 画像を生成しました: {result_path}")
        print(f"  ファイルサイズ: {file_size / 1024:.1f} KB")
    except RuntimeError as e:
        print(f"  NG: 生成に失敗しました: {e}")
        return

    print()
    print("=== テスト完了 ===")


def main():
    """CLIエントリーポイント"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Mermaid図解をPNG画像にレンダリングする"
    )
    parser.add_argument("--input", "-i", help="入力Mermaidファイル (.mmd) のパス")
    parser.add_argument("--output", "-o", help="出力PNGファイルまたはディレクトリのパス")
    parser.add_argument("--request", "-r", help="image_requests.json のパス（一括変換モード）")
    parser.add_argument("--width", "-w", type=int, default=1200, help="画像の幅 (デフォルト: 1200)")
    parser.add_argument("--height", "-H", type=int, default=800, help="画像の高さ (デフォルト: 800)")
    parser.add_argument("--theme", "-t", help="テーマ名 (default, dark, forest, neutral)")
    parser.add_argument("--background", "-b", default="white", help="背景色 (デフォルト: white)")
    parser.add_argument("--api", action="store_true", help="mermaid.ink API を優先して使用する")
    parser.add_argument("--test", action="store_true", help="動作確認テストを実行")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    renderer = MermaidRenderer(prefer_api=args.api if hasattr(args, 'api') else False)

    if args.test:
        _run_test()
        return

    if args.request:
        if not args.output:
            parser.error("--request を使用する場合は --output でディレクトリを指定してください")
        results = renderer.render_from_requests(args.request, args.output)
        print(f"一括変換完了: {len(results)} 件の図解を生成しました")
        for r in results:
            print(f"  {r['id']}: {r['path']}")
        return

    if args.input:
        if not args.output:
            input_path = Path(args.input)
            args.output = str(input_path.with_suffix(".png"))

        with open(args.input, "r", encoding="utf-8") as f:
            mermaid_code = f.read()

        result_path = renderer.render(
            mermaid_code=mermaid_code,
            output_path=args.output,
            width=args.width,
            height=args.height,
            theme=args.theme,
            background=args.background,
        )
        print(f"変換完了: {result_path}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
