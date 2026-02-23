"""
ブラウザスクリーンショットキャプチャモジュール

Playwright（ヘッドレスChromium）を使用して、Webページのスクリーンショットを
PNG画像として保存する。ブログ記事でWebサービスの画面を紹介する際に使用する。

使用方法:
    # image_requests.json の screenshots セクションから一括キャプチャ
    python lib/screenshot_capturer.py --request drafts/slug/image_requests.json --output drafts/slug/images/

    # 単一URLのスクリーンショット
    python lib/screenshot_capturer.py --url https://claude.ai --output screenshot.png

    # 動作確認テスト
    python lib/screenshot_capturer.py --test
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# プロジェクト内モジュールのインポートを可能にする
_lib_dir = Path(__file__).resolve().parent
if str(_lib_dir.parent) not in sys.path:
    sys.path.insert(0, str(_lib_dir.parent))

from lib import config  # noqa: E402

# ロガー設定
logger = logging.getLogger(__name__)


class ScreenshotError(Exception):
    """スクリーンショット取得に失敗した際の例外"""
    pass


class ScreenshotCapturer:
    """Playwright を使ったWebページスクリーンショットキャプチャ。

    ヘッドレスChromiumブラウザでページを開き、PNG画像として保存する。
    Cookie同意バナーの自動クリックや日本語フォント対応も含む。
    """

    # デフォルト設定
    DEFAULT_VIEWPORT_WIDTH = 1280
    DEFAULT_VIEWPORT_HEIGHT = 800
    DEFAULT_WAIT_SECONDS = 3
    DEFAULT_TIMEOUT_MS = 30000

    # Cookie同意バナーの一般的なセレクタ（自動クリック用）
    _COOKIE_DISMISS_SELECTORS = [
        'button[id*="accept"]',
        'button[id*="consent"]',
        'button[class*="accept"]',
        'button[class*="consent"]',
        'a[id*="accept"]',
        '[data-testid*="accept"]',
        '[data-testid*="cookie"] button',
    ]

    def __init__(self):
        """ScreenshotCapturer を初期化する。"""
        logger.info("ScreenshotCapturer を初期化しました")

    def capture(
        self,
        url: str,
        output_path: str,
        viewport_width: int = None,
        viewport_height: int = None,
        full_page: bool = False,
        wait_seconds: int = None,
        dismiss_cookies: bool = True,
    ) -> str:
        """URLのスクリーンショットをPNG画像として保存する。

        Args:
            url: キャプチャ対象のURL
            output_path: 保存先ファイルパス
            viewport_width: ビューポート幅（デフォルト: 1280px）
            viewport_height: ビューポート高さ（デフォルト: 800px）
            full_page: True の場合、ページ全体をキャプチャ
            wait_seconds: ページ読み込み後の追加待機秒数（デフォルト: 3秒）
            dismiss_cookies: Cookie同意バナーの自動クリックを試みるか

        Returns:
            保存先の絶対パス文字列

        Raises:
            ScreenshotError: スクリーンショット取得に失敗した場合
        """
        viewport_width = viewport_width or self.DEFAULT_VIEWPORT_WIDTH
        viewport_height = viewport_height or self.DEFAULT_VIEWPORT_HEIGHT
        wait_seconds = wait_seconds if wait_seconds is not None else self.DEFAULT_WAIT_SECONDS

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "スクリーンショット取得開始: %s (viewport: %dx%d)",
            url, viewport_width, viewport_height,
        )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--lang=ja-JP",
                    ],
                )

                context = browser.new_context(
                    viewport={"width": viewport_width, "height": viewport_height},
                    locale="ja-JP",
                    timezone_id="Asia/Tokyo",
                    # ダークモード無効化（ブログ記事用に明るい画面が好ましい）
                    color_scheme="light",
                )

                page = context.new_page()

                # ページ遷移
                try:
                    page.goto(url, wait_until="networkidle", timeout=self.DEFAULT_TIMEOUT_MS)
                except PlaywrightTimeout:
                    logger.warning("networkidle タイムアウト。load 完了で続行します。")
                    try:
                        page.goto(url, wait_until="load", timeout=self.DEFAULT_TIMEOUT_MS)
                    except PlaywrightTimeout:
                        raise ScreenshotError(
                            f"ページの読み込みがタイムアウトしました: {url}"
                        )

                # Cookie同意バナーの自動クリック
                if dismiss_cookies:
                    self._try_dismiss_cookies(page)

                # 追加の待機時間（動的コンテンツの読み込み完了を待つ）
                if wait_seconds > 0:
                    page.wait_for_timeout(wait_seconds * 1000)

                # スクリーンショット取得
                page.screenshot(
                    path=str(output_path),
                    full_page=full_page,
                    type="png",
                )

                browser.close()

            file_size = output_path.stat().st_size
            logger.info(
                "スクリーンショットを保存しました: %s (%.1f KB)",
                output_path, file_size / 1024,
            )
            return str(output_path.resolve())

        except ScreenshotError:
            raise
        except Exception as e:
            raise ScreenshotError(
                f"スクリーンショットの取得に失敗しました: {url}\n詳細: {e}"
            )

    def capture_from_requests(
        self, requests_path: str, output_dir: str
    ) -> list[dict]:
        """image_requests.json の screenshots セクションからスクリーンショットを一括取得する。

        Args:
            requests_path: image_requests.json のパス
            output_dir: 画像出力先ディレクトリ

        Returns:
            取得結果のリスト:
            [{"id": "screenshot_1", "path": "...", "alt": "...", "caption": "..."}]
        """
        requests_path = Path(requests_path)
        output_dir = Path(output_dir)

        if not requests_path.exists():
            raise FileNotFoundError(
                f"リクエストファイルが見つかりません: {requests_path}"
            )

        with open(requests_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        screenshots = data.get("screenshots", [])
        if not screenshots:
            logger.info("screenshots セクションがありません: %s", requests_path)
            return []

        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        total = len(screenshots)

        for i, ss_req in enumerate(screenshots):
            ss_id = ss_req.get("id", f"screenshot_{i + 1}")
            url = ss_req.get("url", "")
            alt = ss_req.get("alt", "")
            caption = ss_req.get("caption", "")
            viewport_width = ss_req.get("viewport_width", self.DEFAULT_VIEWPORT_WIDTH)
            viewport_height = ss_req.get("viewport_height", self.DEFAULT_VIEWPORT_HEIGHT)
            full_page = ss_req.get("full_page", False)
            wait_seconds = ss_req.get("wait_seconds", self.DEFAULT_WAIT_SECONDS)

            if not url:
                logger.warning("screenshot %s: URL が空のためスキップ", ss_id)
                continue

            output_path = output_dir / f"{ss_id}.png"

            logger.info(
                "スクリーンショット [%s] を取得中... (%d/%d) URL: %s",
                ss_id, i + 1, total, url,
            )

            try:
                saved_path = self.capture(
                    url=url,
                    output_path=str(output_path),
                    viewport_width=viewport_width,
                    viewport_height=viewport_height,
                    full_page=full_page,
                    wait_seconds=wait_seconds,
                )
                results.append({
                    "id": ss_id,
                    "path": str(Path(saved_path).relative_to(output_dir.parent)),
                    "alt": alt,
                    "caption": caption,
                })
                logger.info("screenshot %s: 取得成功 -> %s", ss_id, saved_path)
            except ScreenshotError as e:
                logger.error("screenshot %s: 取得失敗 - %s", ss_id, e)

        logger.info("一括キャプチャ完了: %d/%d 件成功", len(results), total)
        return results

    def _try_dismiss_cookies(self, page) -> None:
        """Cookie同意バナーの自動クリックを試みる（失敗しても続行）。"""
        for selector in self._COOKIE_DISMISS_SELECTORS:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    element.click()
                    logger.debug("Cookie バナーをクリックしました: %s", selector)
                    page.wait_for_timeout(500)
                    return
            except Exception:
                continue


# ──────────────────────────────────────────────
# CLI インターフェース
# ──────────────────────────────────────────────

def _run_test():
    """動作確認テスト。サンプルURLのスクリーンショットを取得する。"""
    print("=" * 50)
    print("スクリーンショットキャプチャ 動作確認テスト")
    print("=" * 50)

    test_url = "https://claude.ai"
    test_dir = Path(config.DRAFTS_DIR) / "_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_output = test_dir / "test_screenshot.png"

    print(f"\nテスト対象URL: {test_url}")
    print(f"出力先: {test_output}")

    try:
        capturer = ScreenshotCapturer()
        result_path = capturer.capture(
            url=test_url,
            output_path=str(test_output),
        )
        file_size = test_output.stat().st_size
        print(f"\nテスト成功! スクリーンショットを保存しました: {result_path}")
        print(f"ファイルサイズ: {file_size / 1024:.1f} KB")

    except ScreenshotError as e:
        print(f"\nスクリーンショット取得エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n予期しないエラー: {e}")
        print("\nPlaywrightがインストールされていない場合:")
        print("  uv run playwright install chromium")
        sys.exit(1)


def main():
    """CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(
        description="Webページのスクリーンショットをキャプチャする（Playwright）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # image_requests.json から一括キャプチャ
  python lib/screenshot_capturer.py --request drafts/slug/image_requests.json --output drafts/slug/images/

  # 単一URLのスクリーンショット
  python lib/screenshot_capturer.py --url https://claude.ai --output screenshot.png

  # 動作確認テスト
  python lib/screenshot_capturer.py --test
        """,
    )

    parser.add_argument(
        "--request", "-r",
        type=str,
        help="image_requests.json のパス（一括キャプチャモード）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="出力先ファイルまたはディレクトリのパス",
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="キャプチャ対象のURL（単一URL モード）",
    )
    parser.add_argument(
        "--width", "-w",
        type=int,
        default=1280,
        help="ビューポート幅（デフォルト: 1280）",
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=800,
        help="ビューポート高さ（デフォルト: 800）",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="ページ全体をキャプチャする",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=3,
        help="ページ読み込み後の追加待機秒数（デフォルト: 3）",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="動作確認テストを実行",
    )

    args = parser.parse_args()

    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # テストモード
    if args.test:
        _run_test()
        return

    # 一括キャプチャモード
    if args.request:
        if not args.output:
            parser.error("--request を使用する場合は --output でディレクトリを指定してください")

        requests_path = Path(args.request)
        if not requests_path.exists():
            print(f"エラー: ファイルが見つかりません: {requests_path}")
            sys.exit(1)

        try:
            capturer = ScreenshotCapturer()
            results = capturer.capture_from_requests(
                requests_path=str(requests_path),
                output_dir=args.output,
            )
            print(f"\n一括キャプチャ完了: {len(results)} 件のスクリーンショットを取得しました")
            for r in results:
                print(f"  {r['id']}: {r['path']}")
        except ScreenshotError as e:
            print(f"スクリーンショット取得エラー: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"予期しないエラー: {e}")
            sys.exit(1)

        return

    # 単一URLモード
    if args.url:
        if not args.output:
            parser.error("--url を使用する場合は --output で出力先ファイルを指定してください")

        try:
            capturer = ScreenshotCapturer()
            result_path = capturer.capture(
                url=args.url,
                output_path=args.output,
                viewport_width=args.width,
                viewport_height=args.height,
                full_page=args.full_page,
                wait_seconds=args.wait,
            )
            file_size = Path(result_path).stat().st_size
            print(f"スクリーンショットを保存しました: {result_path}")
            print(f"ファイルサイズ: {file_size / 1024:.1f} KB")
        except ScreenshotError as e:
            print(f"スクリーンショット取得エラー: {e}")
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
