"""
Playwrightを使ってMermaidダイアグラムをPNG画像に変換する。

arm64 Mac でも動作する（Puppeteerのx64/arm64混在問題を回避）。
"""

import base64
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


MERMAID_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 20px; background: white; font-family: 'Helvetica Neue', Arial, sans-serif; }}
  .mermaid {{ display: flex; justify-content: center; }}
</style>
</head>
<body>
<div class="mermaid">
{mermaid_code}
</div>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'default',
    themeVariables: {{
      fontSize: '16px'
    }}
  }});
</script>
</body>
</html>
"""


def render_mermaid_png(mermaid_code: str, output_path: str, width: int = 1200) -> str:
    """PlaywrightのChromiumでMermaidコードをPNGに変換する。

    Args:
        mermaid_code: Mermaid記法のコード
        output_path: 出力PNGのパス
        width: ビューポート幅

    Returns:
        出力ファイルの絶対パス
    """
    from playwright.sync_api import sync_playwright
    import tempfile
    import os

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = MERMAID_HTML_TEMPLATE.format(mermaid_code=mermaid_code)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": 900})

            # set_content() で直接HTMLを設定（CDN importがfile://より安定）
            page.set_content(html_content, wait_until="networkidle")

            # SVGレンダリング完了まで待つ
            try:
                page.wait_for_selector(".mermaid svg", timeout=15000)
            except Exception:
                # タイムアウトしても続行（SVGが既にある場合もある）
                pass

            # 少し待機してレンダリングを安定させる
            page.wait_for_timeout(500)

            # SVG要素のスクリーンショット
            svg_element = page.query_selector(".mermaid svg")
            if svg_element:
                svg_element.screenshot(path=str(output_path))
            else:
                # フォールバック: .mermaid div全体
                mermaid_div = page.query_selector(".mermaid")
                if mermaid_div:
                    mermaid_div.screenshot(path=str(output_path))
                else:
                    page.screenshot(path=str(output_path), full_page=True)

            browser.close()

        logger.info("Playwright で Mermaid PNG 生成完了: %s", output_path)
        return str(output_path.resolve())

    finally:
        pass


def render_from_requests(requests_path: str, output_dir: str) -> list[dict]:
    """image_requests.json の diagrams セクションから一括生成する。"""
    requests_path = Path(requests_path)
    output_dir = Path(output_dir)

    with open(requests_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        diagrams = [item for item in data if item.get("type") == "mermaid"]
    else:
        diagrams = data.get("diagrams", [])

    if not diagrams:
        logger.warning("Mermaid diagrams が見つかりません")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for diagram in diagrams:
        diagram_id = diagram.get("id", "unknown")
        mermaid_code = diagram.get("mermaid_code", "")
        alt = diagram.get("alt", "")
        caption = diagram.get("caption", "")

        if not mermaid_code:
            continue

        output_path = output_dir / f"{diagram_id}.png"
        try:
            rendered_path = render_mermaid_png(mermaid_code, str(output_path))
            results.append({"id": diagram_id, "path": rendered_path, "alt": alt, "caption": caption})
            print(f"  OK: {diagram_id} -> {rendered_path}")
        except Exception as e:
            logger.error("diagram %s: 失敗 - %s", diagram_id, e)
            results.append({"id": diagram_id, "path": None, "error": str(e), "alt": alt, "caption": caption})
            print(f"  NG: {diagram_id} -> {e}")

    return results


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="PlaywrightでMermaidをPNGに変換")
    parser.add_argument("--request", "-r", help="image_requests.json のパス")
    parser.add_argument("--output", "-o", help="出力ディレクトリ")
    parser.add_argument("--input", "-i", help="Mermaidコードファイル (.mmd)")
    parser.add_argument("--width", type=int, default=1200)
    args = parser.parse_args()

    if args.request and args.output:
        results = render_from_requests(args.request, args.output)
        print(f"完了: {len([r for r in results if r.get('path')])} / {len(results)} 件成功")
    elif args.input and args.output:
        with open(args.input, encoding="utf-8") as f:
            code = f.read()
        path = render_mermaid_png(code, args.output, args.width)
        print(f"変換完了: {path}")
    else:
        parser.print_help()
