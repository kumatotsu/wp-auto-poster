"""
もしもアフィリエイト「かんたんリンク」HTML生成スクリプト

書籍情報（タイトル、ASIN、画像URL、出版社、検索キーワード）から
もしもアフィリエイトの「かんたんリンク」形式のHTMLを自動生成する。

Usage:
    python lib/affiliate_linker.py \
        --request ../drafts/{slug}/affiliate_links.json \
        --output ../drafts/{slug}/affiliate_section.html
"""

import argparse
import json
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

# ──────────────────────────────────────────────
# config読み込み（直接実行 / パッケージインポート両対応）
# ──────────────────────────────────────────────
try:
    from lib.config import (
        MOSHIMO_AMAZON_AID, MOSHIMO_RAKUTEN_AID,
        MOSHIMO_AMAZON_PLID, MOSHIMO_RAKUTEN_PLID,
        MOSHIMO_AMAZON_PID, MOSHIMO_AMAZON_PCID,
        MOSHIMO_RAKUTEN_PID, MOSHIMO_RAKUTEN_PCID,
        MOSHIMO_SCRIPT_URL,
        validate_moshimo_config,
    )
except ImportError:
    from config import (
        MOSHIMO_AMAZON_AID, MOSHIMO_RAKUTEN_AID,
        MOSHIMO_AMAZON_PLID, MOSHIMO_RAKUTEN_PLID,
        MOSHIMO_AMAZON_PID, MOSHIMO_AMAZON_PCID,
        MOSHIMO_RAKUTEN_PID, MOSHIMO_RAKUTEN_PCID,
        MOSHIMO_SCRIPT_URL,
        validate_moshimo_config,
    )


# ──────────────────────────────────────────────
# かんたんリンクHTMLテンプレート
# ──────────────────────────────────────────────

# JavaScriptローダー部分（全リンク共通）
_MSMAFLINK_LOADER = (
    '(function(b,c,f,g,a,d,e){{b.MoshimoAffiliateObject=a;'
    'b[a]=b[a]||function(){{arguments.currentScript=c.currentScript'
    '||c.scripts[c.scripts.length-2];(b[a].q=b[a].q||[]).push(arguments)}};'
    'c.getElementById(a)||(d=c.createElement(f),d.src=g,d.id=a,'
    'e=c.getElementsByTagName("body")[0],e.appendChild(d))}})'
    '(window,document,"script","{script_url}","msmaflink")'
)


def _generate_unique_id() -> str:
    """かんたんリンク用のユニークID（5文字）を生成する。"""
    return uuid.uuid4().hex[:5]


def _escape_json_string(s: str) -> str:
    """JSON文字列内のエスケープが必要な文字を処理する。"""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('/', '\\/')


class MoshimoEasyLinkGenerator:
    """
    もしもアフィリエイト「かんたんリンク」HTML生成クラス

    書籍情報からmsmaflink形式のHTMLスニペットを生成する。
    """

    def __init__(
        self,
        amazon_aid: str = None,
        rakuten_aid: str = None,
        amazon_plid: str = None,
        rakuten_plid: str = None,
        script_url: str = None,
    ):
        """
        初期化。引数省略時は config.py の値を使用する。

        Args:
            amazon_aid: Amazon用もしもアフィリエイトID
            rakuten_aid: 楽天用もしもアフィリエイトID
            amazon_plid: Amazon用プロモーションリンクID
            rakuten_plid: 楽天用プロモーションリンクID
            script_url: かんたんリンクのスクリプトURL
        """
        self.amazon_aid = amazon_aid or MOSHIMO_AMAZON_AID
        self.rakuten_aid = rakuten_aid or MOSHIMO_RAKUTEN_AID
        self.amazon_plid = amazon_plid or MOSHIMO_AMAZON_PLID
        self.rakuten_plid = rakuten_plid or MOSHIMO_RAKUTEN_PLID
        self.script_url = script_url or MOSHIMO_SCRIPT_URL

    def generate_easy_link(self, book: dict) -> str:
        """
        1冊分のかんたんリンクHTMLを生成する。

        Args:
            book: 書籍情報の辞書
                - title (str): 書籍タイトル（必須）
                - keyword (str): 検索キーワード（必須）
                - asin (str): Amazon ASIN（任意）
                - image_url (str): 商品画像URL（任意）
                - publisher (str): 出版社名（任意）
                - rakuten_url (str): 楽天商品URL（任意）

        Returns:
            str: かんたんリンクHTML
        """
        title = book.get("title", "")
        keyword = book.get("keyword", title)
        asin = book.get("asin", "")
        image_url = book.get("image_url", "")
        publisher = book.get("publisher", "")
        rakuten_url = book.get("rakuten_url", "")
        eid = _generate_unique_id()

        # Amazon検索URL（ASINがある場合は直接商品ページ、ない場合は検索）
        if asin:
            amazon_url = f"https:\\/\\/www.amazon.co.jp\\/dp\\/{asin}"
        else:
            encoded_keyword = quote(keyword)
            amazon_url = (
                f"https:\\/\\/www.amazon.co.jp\\/s\\/ref=nb_sb_noss_1"
                f"?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A"
                f"\\u0026url=search-alias%3Daps"
                f"\\u0026field-keywords={encoded_keyword}"
            )

        # 楽天URL（指定がある場合はそのまま、ない場合は検索URL）
        if rakuten_url:
            r_url = _escape_json_string(rakuten_url)
        else:
            encoded_keyword_rakuten = quote(keyword)
            r_url = (
                f"https:\\/\\/search.rakuten.co.jp\\/search\\/mall\\/"
                f"{encoded_keyword_rakuten}\\/"
            )

        # 画像URL処理
        # 楽天の画像URL形式: "d"がベースURL、"p"がパス配列
        # Amazon画像URL形式: "d"がフルURL、"c_p"と"p"は空
        if image_url:
            escaped_image = _escape_json_string(image_url)
            image_d = escaped_image
            image_c_p = ""
            image_p = "[]"
        else:
            image_d = ""
            image_c_p = ""
            image_p = "[]"

        # メインURLの決定（楽天URLがあれば楽天、なければAmazon）
        if rakuten_url:
            main_url = _escape_json_string(rakuten_url)
            main_type = "rakuten"
        elif asin:
            main_url = f"https:\\/\\/www.amazon.co.jp\\/dp\\/{asin}"
            main_type = "amazon"
        else:
            main_url = amazon_url
            main_type = "amazon"

        escaped_title = _escape_json_string(title)
        escaped_publisher = _escape_json_string(publisher)

        # msmaflink パラメータ構築
        msmaflink_params = (
            f'{{"n":"{escaped_title}",'
            f'"b":"{escaped_publisher}",'
            f'"t":"{asin}",'
            f'"d":"{image_d}",'
            f'"c_p":"{image_c_p}",'
            f'"p":{image_p},'
            f'"u":{{"u":"{main_url}","t":"{main_type}","r_v":""}},'
            f'"v":"2.1",'
            f'"b_l":['
            f'{{"id":1,"u_tx":"楽天市場","u_bc":"#f76956",'
            f'"u_url":"{r_url}",'
            f'"a_id":{self.rakuten_aid},'
            f'"p_id":{MOSHIMO_RAKUTEN_PID},'
            f'"pl_id":{self.rakuten_plid},'
            f'"pc_id":{MOSHIMO_RAKUTEN_PCID},'
            f'"s_n":"rakuten","u_so":1}},'
            f'{{"id":2,"u_tx":"Amazon","u_bc":"#f79256",'
            f'"u_url":"{amazon_url}",'
            f'"a_id":{self.amazon_aid},'
            f'"p_id":{MOSHIMO_AMAZON_PID},'
            f'"pl_id":{self.amazon_plid},'
            f'"pc_id":{MOSHIMO_AMAZON_PCID},'
            f'"s_n":"amazon","u_so":2}}'
            f'],'
            f'"eid":"{eid}","s":"s"}}'
        )

        # JavaScript ローダー
        loader = _MSMAFLINK_LOADER.format(script_url=self.script_url)

        # 完全なHTMLスニペット
        html = (
            f'<!-- START MoshimoAffiliateEasyLink -->'
            f'<script type="text/javascript">'
            f'{loader};'
            f'msmaflink({msmaflink_params});'
            f'</script>'
            f'<div id="msmaflink-{eid}">リンク</div>'
            f'<!-- MoshimoAffiliateEasyLink END -->'
        )

        return html

    def generate_book_section(
        self,
        books: list[dict],
        heading: str = "あわせて読みたいおすすめ書籍",
        intro_text: str = "",
    ) -> str:
        """
        書籍紹介セクション全体のGutenbergブロック形式HTMLを生成する。

        Args:
            books: 書籍情報のリスト
            heading: セクション見出し（H2）
            intro_text: 導入テキスト（省略時はデフォルト文）

        Returns:
            str: Gutenbergブロック形式の完全なセクションHTML
        """
        if not books:
            return ""

        # デフォルト導入テキスト
        if not intro_text:
            intro_text = (
                "この記事の内容をさらに深く理解するために、"
                "以下の書籍もおすすめです。"
            )

        # H2見出し
        section_parts = [
            '<!-- wp:heading {"level":2} -->',
            f'<h2 class="wp-block-heading">{heading}</h2>',
            '<!-- /wp:heading -->',
            '',
            '<!-- wp:paragraph -->',
            f'<p>{intro_text}</p>',
            '<!-- /wp:paragraph -->',
        ]

        # 各書籍のかんたんリンク
        for book in books:
            easy_link_html = self.generate_easy_link(book)
            section_parts.extend([
                '',
                '<!-- wp:html -->',
                easy_link_html,
                '<!-- /wp:html -->',
            ])

        return '\n'.join(section_parts)


# ──────────────────────────────────────────────
# CLI インターフェース
# ──────────────────────────────────────────────

def main():
    """コマンドラインからの実行エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="もしもアフィリエイト かんたんリンクHTML生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python lib/affiliate_linker.py --request ../drafts/test/affiliate_links.json --output ../drafts/test/affiliate_section.html
        """,
    )
    parser.add_argument(
        "--request",
        required=True,
        help="書籍情報JSONファイルのパス（affiliate_links.json）",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="出力先HTMLファイルのパス（affiliate_section.html）",
    )

    args = parser.parse_args()

    # 設定バリデーション
    errors = validate_moshimo_config()
    if errors:
        print("[エラー] もしもアフィリエイト設定に問題があります:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # リクエストファイル読み込み
    request_path = Path(args.request)
    if not request_path.exists():
        print(f"[エラー] リクエストファイルが見つかりません: {args.request}")
        sys.exit(1)

    with open(request_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    books = data.get("books", [])
    heading = data.get("heading", "あわせて読みたいおすすめ書籍")
    intro_text = data.get("intro_text", "")

    if not books:
        print("[警告] 書籍データが空です。HTMLは生成されません。")
        # 空のファイルを出力
        output_path = Path(args.output)
        output_path.write_text("", encoding="utf-8")
        return

    print(f"かんたんリンク生成開始（{len(books)}冊）")

    # HTML生成
    generator = MoshimoEasyLinkGenerator()
    section_html = generator.generate_book_section(
        books=books,
        heading=heading,
        intro_text=intro_text,
    )

    # 出力
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(section_html, encoding="utf-8")

    print(f"[OK] かんたんリンクHTML生成完了: {args.output}")
    for i, book in enumerate(books, 1):
        print(f"  [{i}] {book.get('title', '(タイトル未設定)')}")


if __name__ == "__main__":
    main()
