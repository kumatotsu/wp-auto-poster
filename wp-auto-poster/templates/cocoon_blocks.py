"""
Cocoonテーマ対応 Gutenberg ブロック HTML 生成ヘルパー

WordPress Gutenbergエディタのブロック形式HTMLを生成する。
Cocoonテーマ固有のボックス装飾・吹き出しにも対応。

生成されるHTMLはWordPress REST APIでそのまま投稿可能な形式。
"""

import json
from html import escape


# ──────────────────────────────────────────────
# 標準Gutenbergブロック
# ──────────────────────────────────────────────

def heading_block(text: str, level: int = 2) -> str:
    """
    見出しブロックを生成する（H2〜H4）。

    Args:
        text: 見出しテキスト
        level: 見出しレベル（2, 3, 4）

    Returns:
        str: Gutenberg見出しブロックHTML
    """
    if level not in (2, 3, 4):
        raise ValueError(f"見出しレベルは 2〜4 を指定してください（指定値: {level}）")

    attrs = json.dumps({"level": level})
    return (
        f'<!-- wp:heading {attrs} -->\n'
        f'<h{level} class="wp-block-heading">{escape(text)}</h{level}>\n'
        f'<!-- /wp:heading -->'
    )


def paragraph_block(text: str) -> str:
    """
    段落ブロックを生成する。

    テキスト内の改行は <br> に変換される。
    HTMLタグ（<strong>, <em>, <a> 等）はそのまま保持される。

    Args:
        text: 段落テキスト（HTML可）

    Returns:
        str: Gutenberg段落ブロックHTML
    """
    # テキスト内の改行を <br> に変換（ただし既にHTMLタグがある場合はそのまま）
    formatted = text.replace("\n", "<br>")
    return (
        f'<!-- wp:paragraph -->\n'
        f'<p>{formatted}</p>\n'
        f'<!-- /wp:paragraph -->'
    )


def image_block(url: str, alt: str = "", caption: str = "",
                media_id: int = None, width: int = None) -> str:
    """
    画像ブロックを生成する（WordPress標準画像ブロック形式）。

    Args:
        url: 画像のURL
        alt: 代替テキスト
        caption: キャプション
        media_id: WordPressメディアID
        width: 画像の表示幅（ピクセル）

    Returns:
        str: Gutenberg画像ブロックHTML
    """
    # ブロック属性
    block_attrs = {}
    if media_id:
        block_attrs["id"] = media_id
    if width:
        block_attrs["width"] = width

    attrs_str = f" {json.dumps(block_attrs)}" if block_attrs else ""

    # <img> タグ
    img_classes = []
    if media_id:
        img_classes.append(f"wp-image-{media_id}")
    class_attr = f' class="{" ".join(img_classes)}"' if img_classes else ""

    width_attr = f' width="{width}"' if width else ""
    img_tag = f'<img src="{escape(url)}" alt="{escape(alt)}"{class_attr}{width_attr}/>'

    # <figure> タグ
    figure_class = "wp-block-image size-large"

    if caption:
        figure_html = (
            f'<figure class="{figure_class}">'
            f'{img_tag}'
            f'<figcaption class="wp-element-caption">{escape(caption)}</figcaption>'
            f'</figure>'
        )
    else:
        figure_html = (
            f'<figure class="{figure_class}">'
            f'{img_tag}'
            f'</figure>'
        )

    return (
        f'<!-- wp:image{attrs_str} -->\n'
        f'{figure_html}\n'
        f'<!-- /wp:image -->'
    )


def list_block(items: list[str], ordered: bool = False) -> str:
    """
    リストブロックを生成する。

    Args:
        items: リスト項目のテキストリスト
        ordered: True で番号付きリスト、False で箇条書き

    Returns:
        str: GutenbergリストブロックHTML
    """
    block_name = "list"
    attrs = ""
    if ordered:
        attrs = f' {json.dumps({"ordered": True})}'

    tag = "ol" if ordered else "ul"
    li_items = "\n".join(f'<li>{item}</li>' for item in items)

    return (
        f'<!-- wp:{block_name}{attrs} -->\n'
        f'<{tag} class="wp-block-list">\n'
        f'{li_items}\n'
        f'</{tag}>\n'
        f'<!-- /wp:{block_name} -->'
    )


def code_block(code: str, language: str = "") -> str:
    """
    コードブロックを生成する。

    Args:
        code: コード文字列
        language: プログラミング言語名（シンタックスハイライト用）

    Returns:
        str: GutenbergコードブロックHTML
    """
    attrs = ""
    if language:
        attrs = f' {json.dumps({"language": language})}'

    return (
        f'<!-- wp:code{attrs} -->\n'
        f'<pre class="wp-block-code"><code>{escape(code)}</code></pre>\n'
        f'<!-- /wp:code -->'
    )


def quote_block(text: str, citation: str = "") -> str:
    """
    引用ブロックを生成する。

    Args:
        text: 引用テキスト
        citation: 引用元の情報

    Returns:
        str: Gutenberg引用ブロックHTML
    """
    cite_html = f'\n<cite>{escape(citation)}</cite>' if citation else ""
    return (
        f'<!-- wp:quote -->\n'
        f'<blockquote class="wp-block-quote">\n'
        f'<p>{escape(text)}</p>{cite_html}\n'
        f'</blockquote>\n'
        f'<!-- /wp:quote -->'
    )


def table_block(headers: list[str], rows: list[list[str]]) -> str:
    """
    テーブルブロックを生成する。

    Args:
        headers: ヘッダー行のテキストリスト
        rows: データ行のリスト（各行はテキストのリスト）

    Returns:
        str: GutenbergテーブルブロックHTML
    """
    # ヘッダー行
    th_cells = "".join(f"<th>{escape(h)}</th>" for h in headers)
    thead = f"<thead><tr>{th_cells}</tr></thead>"

    # データ行
    body_rows = []
    for row in rows:
        td_cells = "".join(f"<td>{escape(cell)}</td>" for cell in row)
        body_rows.append(f"<tr>{td_cells}</tr>")
    tbody = f"<tbody>{''.join(body_rows)}</tbody>"

    attrs = json.dumps({"hasFixedLayout": True})

    return (
        f'<!-- wp:table {attrs} -->\n'
        f'<figure class="wp-block-table">\n'
        f'<table class="has-fixed-layout">\n'
        f'{thead}\n'
        f'{tbody}\n'
        f'</table>\n'
        f'</figure>\n'
        f'<!-- /wp:table -->'
    )


# ──────────────────────────────────────────────
# Cocoonテーマ固有ブロック
# ──────────────────────────────────────────────

# Cocoonボックスのスタイル定義
# style名 -> (CSSクラス, アイコンクラス)
_COCOON_BOX_STYLES = {
    "info":    ("blank-box bb-tab bb-blue",   "fa-info-circle"),
    "warning": ("blank-box bb-tab bb-yellow", "fa-exclamation-triangle"),
    "tip":     ("blank-box bb-tab bb-green",  "fa-check-circle"),
    "memo":    ("blank-box bb-tab bb-grey",   "fa-pencil"),
    "primary": ("blank-box bb-tab bb-blue",   "fa-info-circle"),
    "success": ("blank-box bb-tab bb-green",  "fa-check"),
    "danger":  ("blank-box bb-tab bb-red",    "fa-times-circle"),
}


def cocoon_box(title: str, content: str, style: str = "info") -> str:
    """
    Cocoonのボックス装飾ブロックを生成する。

    ボックスはCocoonテーマの「タブボックス」スタイルを使用。
    コンテンツにはHTMLを含めることが可能。

    Args:
        title: ボックスのタイトル（タブ部分）
        content: ボックスの内容（HTML可）
        style: スタイル名
               "info" - 情報（青）
               "warning" - 警告（黄）
               "tip" - ヒント/成功（緑）
               "memo" - メモ（灰）
               "primary" - プライマリ（青）
               "success" - 成功（緑）
               "danger" - 危険（赤）

    Returns:
        str: CocoonボックスのHTML
    """
    if style not in _COCOON_BOX_STYLES:
        style = "info"

    box_class, icon_class = _COCOON_BOX_STYLES[style]

    return (
        f'<!-- wp:html -->\n'
        f'<div class="{box_class}">\n'
        f'<div class="bb-label">\n'
        f'<span class="fa {icon_class}"></span>\n'
        f'{escape(title)}\n'
        f'</div>\n'
        f'<div class="bb-content">\n'
        f'{content}\n'
        f'</div>\n'
        f'</div>\n'
        f'<!-- /wp:html -->'
    )


def cocoon_balloon(text: str, name: str = "", icon_url: str = "",
                   position: str = "left") -> str:
    """
    Cocoonの吹き出しブロックを生成する。

    Args:
        text: 吹き出しのテキスト
        name: 話者の名前
        icon_url: アイコン画像のURL
        position: 吹き出しの位置（"left" または "right"）

    Returns:
        str: Cocoon吹き出しのHTML
    """
    if position not in ("left", "right"):
        position = "left"

    # 吹き出しの方向クラス
    direction_class = "sbp-l" if position == "left" else "sbp-r"

    # アイコン部分
    icon_html = ""
    if icon_url or name:
        icon_img = f'<img src="{escape(icon_url)}" alt="{escape(name)}" class="speech-icon-image"/>' if icon_url else ""
        name_html = f'<figcaption class="speech-icon-name">{escape(name)}</figcaption>' if name else ""
        icon_html = (
            f'<figure class="speech-icon">\n'
            f'{icon_img}\n'
            f'{name_html}\n'
            f'</figure>'
        )

    return (
        f'<!-- wp:html -->\n'
        f'<div class="speech-wrap {direction_class} sbs-flat">\n'
        f'{icon_html}\n'
        f'<div class="speech-balloon">\n'
        f'<p>{escape(text)}</p>\n'
        f'</div>\n'
        f'</div>\n'
        f'<!-- /wp:html -->'
    )


# ──────────────────────────────────────────────
# プレースホルダー・アセンブル
# ──────────────────────────────────────────────

def image_placeholder(image_id: str, alt: str = "", caption: str = "") -> str:
    """
    画像プレースホルダーを生成する。

    このプレースホルダーは wp_client.py の publish_draft_from_dir() によって
    画像アップロード後に実際の <figure> ブロックに置換される。

    プレースホルダー形式: <!-- IMAGE: {image_id} -->

    Args:
        image_id: 画像の識別子（image_results.json の id に対応）
        alt: 代替テキスト
        caption: キャプション

    Returns:
        str: 画像プレースホルダーコメント
    """
    attrs = ""
    if alt:
        attrs += f' alt="{alt}"'
    if caption:
        attrs += f' caption="{caption}"'

    return f'<!-- IMAGE: {image_id}{attrs} -->'


def assemble_article(blocks: list[str]) -> str:
    """
    ブロックリストを結合して完全な記事HTMLを生成する。

    各ブロック間に空行を挿入し、Gutenbergエディタで
    正しく解析されるようにフォーマットする。

    Args:
        blocks: ブロックHTMLのリスト

    Returns:
        str: 完全な記事HTML
    """
    # 空のブロックを除外
    valid_blocks = [b for b in blocks if b and b.strip()]

    # ブロック間に空行（2つの改行）を挿入
    return "\n\n".join(valid_blocks)
