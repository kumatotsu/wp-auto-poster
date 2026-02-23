"""
WordPress REST API クライアント

m-totsu.com（とつブログ）への記事投稿・メディアアップロードを行う。
認証にはアプリケーションパスワード方式（Basic認証）を使用する。
"""

import argparse
import json
import mimetypes
import sys
from pathlib import Path

import requests

# ──────────────────────────────────────────────
# config読み込み（直接実行 / パッケージインポート両対応）
# ──────────────────────────────────────────────
try:
    from lib.config import (
        WP_URL, WP_USER, WP_APP_PASSWORD, WP_REST_BASE,
        DRAFTS_DIR, validate_wp_config,
    )
except ImportError:
    from config import (
        WP_URL, WP_USER, WP_APP_PASSWORD, WP_REST_BASE,
        DRAFTS_DIR, validate_wp_config,
    )


class WordPressClientError(Exception):
    """WordPress API操作で発生するエラーの基底クラス"""
    pass


class WordPressAuthError(WordPressClientError):
    """認証エラー"""
    pass


class WordPressAPIError(WordPressClientError):
    """APIリクエストエラー"""
    pass


class WordPressClient:
    """
    WordPress REST API クライアント

    Basic認証を使い、記事の下書き作成・メディアアップロードなどを行う。
    デフォルト値は config.py から読み込まれるが、引数で上書きも可能。
    """

    def __init__(self, url: str = None, user: str = None, password: str = None):
        """
        クライアントを初期化する。

        Args:
            url: WordPressサイトのURL（省略時は config.WP_URL）
            user: ユーザー名（省略時は config.WP_USER）
            password: アプリケーションパスワード（省略時は config.WP_APP_PASSWORD）
        """
        self.site_url = (url or WP_URL).rstrip("/")
        self.user = user or WP_USER
        self.password = password or WP_APP_PASSWORD
        self.rest_base = f"{self.site_url}/wp-json/wp/v2"
        self.auth = (self.user, self.password)

        # セッションを使い回してコネクションを効率化
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "User-Agent": "wp-auto-poster/1.0",
        })

    # ──────────────────────────────────────────
    # 内部ヘルパー
    # ──────────────────────────────────────────

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        REST APIへのリクエストを送り、レスポンスを検証して返す。

        Args:
            method: HTTPメソッド（GET, POST, PUT, DELETE）
            endpoint: エンドポイントパス（例: /posts）
            **kwargs: requests に渡す追加引数

        Returns:
            requests.Response オブジェクト

        Raises:
            WordPressAuthError: 401/403 エラー時
            WordPressAPIError: その他のHTTPエラー時
        """
        url = f"{self.rest_base}{endpoint}"
        try:
            resp = self.session.request(method, url, timeout=30, **kwargs)
        except requests.ConnectionError as e:
            raise WordPressClientError(
                f"接続エラー: {self.site_url} に接続できません。\n詳細: {e}"
            )
        except requests.Timeout:
            raise WordPressClientError(
                f"タイムアウト: {url} からの応答がありません。"
            )

        if resp.status_code in (401, 403):
            raise WordPressAuthError(
                f"認証エラー ({resp.status_code}): "
                f"ユーザー名またはアプリケーションパスワードを確認してください。\n"
                f"レスポンス: {resp.text[:300]}"
            )

        if not resp.ok:
            # APIが返すエラーメッセージを抽出
            try:
                err_data = resp.json()
                msg = err_data.get("message", resp.text[:300])
            except (ValueError, KeyError):
                msg = resp.text[:300]
            raise WordPressAPIError(
                f"APIエラー ({resp.status_code}): {msg}\n"
                f"エンドポイント: {method} {url}"
            )

        return resp

    def _get(self, endpoint: str, params: dict = None) -> requests.Response:
        """GETリクエストのショートカット"""
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, **kwargs) -> requests.Response:
        """POSTリクエストのショートカット"""
        return self._request("POST", endpoint, **kwargs)

    # ──────────────────────────────────────────
    # 接続・認証テスト
    # ──────────────────────────────────────────

    def check_connection(self) -> bool:
        """
        REST APIへの接続を確認する。

        Returns:
            True: 接続成功
            False: 接続失敗

        Note:
            認証なしで /wp-json/ にアクセスし、APIの存在を確認する。
        """
        url = f"{self.site_url}/wp-json/"
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                data = resp.json()
                site_name = data.get("name", "(不明)")
                print(f"[OK] REST API接続成功: {site_name} ({self.site_url})")
                return True
            else:
                print(f"[NG] REST API応答エラー: HTTP {resp.status_code}")
                return False
        except requests.ConnectionError:
            print(f"[NG] 接続失敗: {self.site_url} に到達できません")
            return False
        except Exception as e:
            print(f"[NG] 予期しないエラー: {e}")
            return False

    def check_authentication(self) -> dict:
        """
        認証テストを行い、ログインユーザーの情報を返す。

        Returns:
            dict: {"id": user_id, "name": display_name, "roles": [...]}

        Raises:
            WordPressAuthError: 認証失敗時
        """
        resp = self._get("/users/me", params={"context": "edit"})
        user_data = resp.json()

        result = {
            "id": user_data.get("id"),
            "name": user_data.get("name", ""),
            "slug": user_data.get("slug", ""),
            "roles": user_data.get("roles", []),
        }
        print(f"[OK] 認証成功: {result['name']} (ID: {result['id']}, "
              f"権限: {', '.join(result['roles'])})")
        return result

    # ──────────────────────────────────────────
    # メディアアップロード
    # ──────────────────────────────────────────

    def upload_media(self, file_path: str, alt_text: str = "",
                     title: str = "", caption: str = "") -> dict:
        """
        画像をメディアライブラリにアップロードする。

        Args:
            file_path: アップロードするファイルのパス
            alt_text: 代替テキスト（SEO用）
            title: メディアのタイトル
            caption: キャプション

        Returns:
            dict: {"id": media_id, "url": source_url, "alt": alt_text}

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            WordPressAPIError: アップロード失敗時
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        # MIMEタイプを推定
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # ファイルを読み込んでアップロード
        with open(path, "rb") as f:
            file_data = f.read()

        headers = {
            "Content-Type": mime_type,
            "Content-Disposition": f'attachment; filename="{path.name}"',
        }

        print(f"  アップロード中: {path.name} ({len(file_data) / 1024:.1f} KB)")

        resp = self._post("/media", headers=headers, data=file_data)
        media = resp.json()
        media_id = media["id"]
        source_url = media.get("source_url", "")

        # alt_text, title, caption を更新（指定がある場合）
        update_data = {}
        if alt_text:
            update_data["alt_text"] = alt_text
        if title:
            update_data["title"] = title
        if caption:
            update_data["caption"] = caption

        if update_data:
            self._request("POST", f"/media/{media_id}", json=update_data)

        result = {
            "id": media_id,
            "url": source_url,
            "alt": alt_text or media.get("alt_text", ""),
        }
        print(f"  [OK] アップロード完了: ID={media_id}")
        return result

    def upload_multiple_media(self, files: list[dict]) -> list[dict]:
        """
        複数の画像を一括アップロードする。

        Args:
            files: アップロードファイルのリスト
                   [{"path": "...", "alt": "...", "title": "...", "caption": "..."}]

        Returns:
            list[dict]: 各ファイルのアップロード結果リスト
        """
        results = []
        total = len(files)

        print(f"画像アップロード開始（全{total}件）")
        for i, file_info in enumerate(files, 1):
            print(f"  [{i}/{total}] ", end="")
            try:
                result = self.upload_media(
                    file_path=file_info["path"],
                    alt_text=file_info.get("alt", ""),
                    title=file_info.get("title", ""),
                    caption=file_info.get("caption", ""),
                )
                results.append(result)
            except Exception as e:
                print(f"  [NG] 失敗: {file_info['path']} - {e}")
                results.append({
                    "id": None,
                    "url": None,
                    "alt": file_info.get("alt", ""),
                    "error": str(e),
                })

        success_count = sum(1 for r in results if r.get("id") is not None)
        print(f"画像アップロード完了: {success_count}/{total} 件成功")
        return results

    # ──────────────────────────────────────────
    # 記事投稿
    # ──────────────────────────────────────────

    def create_draft(self, title: str, content: str,
                     featured_media_id: int = None,
                     categories: list[int] = None,
                     tags: list[int] = None,
                     meta: dict = None,
                     slug: str = None) -> dict:
        """
        下書き記事を作成する。

        Args:
            title: 記事タイトル
            content: 記事本文（Gutenbergブロック形式HTML）
            featured_media_id: アイキャッチ画像のメディアID
            categories: カテゴリIDのリスト
            tags: タグIDのリスト
            meta: メタフィールド（Yoast SEO等）
            slug: URLスラッグ

        Returns:
            dict: {"id": post_id, "url": edit_url, "preview_url": preview_url}

        Note:
            status は常に 'draft' で投稿される。
            meta に Yoast SEO フィールドを含めることが可能:
            - _yoast_wpseo_title: SEOタイトル
            - _yoast_wpseo_metadesc: メタディスクリプション
            - _yoast_wpseo_focuskw: フォーカスキーワード
        """
        post_data = {
            "title": title,
            "content": content,
            "status": "draft",
        }

        if featured_media_id:
            post_data["featured_media"] = featured_media_id
        if categories:
            post_data["categories"] = categories
        if tags:
            post_data["tags"] = tags
        if slug:
            post_data["slug"] = slug

        # Yoast SEO メタフィールド
        if meta:
            post_data["meta"] = {}
            yoast_fields = [
                "_yoast_wpseo_title",
                "_yoast_wpseo_metadesc",
                "_yoast_wpseo_focuskw",
            ]
            for field in yoast_fields:
                if field in meta:
                    post_data["meta"][field] = meta[field]
            # その他のカスタムメタフィールドもそのまま渡す
            for key, value in meta.items():
                if key not in yoast_fields:
                    post_data["meta"][key] = value

        print(f"下書き投稿中: 「{title}」")
        resp = self._post("/posts", json=post_data)
        post = resp.json()

        post_id = post["id"]
        # WordPress管理画面の編集URL
        edit_url = f"{self.site_url}/wp-admin/post.php?post={post_id}&action=edit"
        # プレビューURL
        preview_url = post.get("link", "")
        if preview_url:
            preview_url += "?preview=true" if "?" not in preview_url else "&preview=true"

        result = {
            "id": post_id,
            "url": edit_url,
            "preview_url": preview_url,
        }
        print(f"[OK] 下書き作成完了: ID={post_id}")
        print(f"     編集URL: {edit_url}")
        return result

    def update_post(self, post_id: int, content: str,
                    title: str = None,
                    featured_media_id: int = None,
                    categories: list[int] = None,
                    tags: list[int] = None,
                    meta: dict = None,
                    slug: str = None) -> dict:
        """
        既存の記事を更新する（本文・タイトル・メタ等）。

        Args:
            post_id: 更新対象の記事ID
            content: 新しい記事本文（Gutenbergブロック形式HTML）
            title: 新しいタイトル（省略時は変更しない）
            featured_media_id: アイキャッチ画像のメディアID（省略時は変更しない）
            categories: カテゴリIDのリスト（省略時は変更しない）
            tags: タグIDのリスト（省略時は変更しない）
            meta: メタフィールド（Yoast SEO等）
            slug: URLスラッグ（省略時は変更しない）

        Returns:
            dict: {"id": post_id, "url": edit_url, "preview_url": preview_url}

        Note:
            status は変更しない（現在のステータスを維持する）。
        """
        post_data: dict = {"content": content}

        if title is not None:
            post_data["title"] = title
        if featured_media_id is not None:
            post_data["featured_media"] = featured_media_id
        if categories is not None:
            post_data["categories"] = categories
        if tags is not None:
            post_data["tags"] = tags
        if slug is not None:
            post_data["slug"] = slug

        # Yoast SEO メタフィールド
        if meta:
            post_data["meta"] = {}
            yoast_fields = [
                "_yoast_wpseo_title",
                "_yoast_wpseo_metadesc",
                "_yoast_wpseo_focuskw",
            ]
            for field in yoast_fields:
                if field in meta:
                    post_data["meta"][field] = meta[field]
            for key, value in meta.items():
                if key not in yoast_fields:
                    post_data["meta"][key] = value

        print(f"記事更新中: ID={post_id}" + (f" 「{title}」" if title else ""))
        resp = self._request("POST", f"/posts/{post_id}", json=post_data)
        post = resp.json()

        edit_url = f"{self.site_url}/wp-admin/post.php?post={post_id}&action=edit"
        preview_url = post.get("link", "")
        if preview_url:
            preview_url += "?preview=true" if "?" not in preview_url else "&preview=true"

        result = {
            "id": post_id,
            "url": edit_url,
            "preview_url": preview_url,
        }
        print(f"[OK] 記事更新完了: ID={post_id}")
        print(f"     編集URL: {edit_url}")
        return result

    def update_post_from_dir(self, post_id: int, draft_dir: str) -> dict:
        """
        drafts/{slug}/ ディレクトリの内容で既存の記事を更新する。

        既存画像（images/）は再アップロードせず、image_results.json の
        アップロード済み情報（media_id / url）を再利用する。
        新しい画像がある場合のみアップロードする。

        Args:
            post_id: 更新対象の記事ID
            draft_dir: 下書きディレクトリのパス

        Returns:
            dict: {"post_id": ..., "edit_url": ..., "media_ids": [...]}
        """
        draft_path = Path(draft_dir)
        if not draft_path.is_dir():
            raise FileNotFoundError(f"下書きディレクトリが見つかりません: {draft_dir}")

        print(f"{'='*60}")
        print(f"記事更新開始: ID={post_id} / {draft_path.name}")
        print(f"{'='*60}")

        # ── 1. meta.json を読み込み ──
        meta_file = draft_path / "meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"meta.json が見つかりません: {meta_file}")

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        title = meta.get("title")
        slug = meta.get("slug")
        category_names = meta.get("categories", [])
        tag_names = meta.get("tags", [])
        seo_meta = {}
        if "seo_title" in meta:
            seo_meta["_yoast_wpseo_title"] = meta["seo_title"]
        if "seo_description" in meta:
            seo_meta["_yoast_wpseo_metadesc"] = meta["seo_description"]
        if "focus_keyword" in meta:
            seo_meta["_yoast_wpseo_focuskw"] = meta["focus_keyword"]
        # yoast_seo フィールドも直接読み込む
        yoast = meta.get("yoast_seo", {})
        for k, v in yoast.items():
            seo_meta[k] = v

        print(f"タイトル: {title}")

        # ── 2. 画像マップの構築（アップロード済み情報を再利用） ──
        image_map = {}
        featured_media_id = None
        media_ids = []

        image_results_file = draft_path / "image_results.json"
        image_results = {}
        if image_results_file.exists():
            with open(image_results_file, "r", encoding="utf-8") as f:
                image_results = json.load(f)

        # image_results.json に uploaded_media が記録されていれば再利用
        uploaded = image_results.get("uploaded_media", {})
        if uploaded:
            print("\n画像: アップロード済み情報を再利用します")
            for img_id, img_data in uploaded.items():
                image_map[img_id] = img_data
                media_ids.append(img_data.get("media_id"))
                if img_data.get("eyecatch"):
                    featured_media_id = img_data.get("media_id")
            if featured_media_id is None and media_ids:
                featured_media_id = media_ids[0]
        else:
            # 既存画像ディレクトリがある場合は再アップロード（フォールバック）
            images_dir = draft_path / "images"
            if images_dir.is_dir():
                image_files = sorted(
                    p for p in images_dir.iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
                )
                if image_files:
                    print(f"\n画像再アップロード（{len(image_files)}件）:")
                    for img_path in image_files:
                        img_info = _find_image_info(image_results, img_path.name)
                        alt_text = img_info.get("alt", "")
                        image_id = img_info.get("id", img_path.stem)
                        result = self.upload_media(
                            file_path=str(img_path),
                            alt_text=alt_text,
                            title=img_info.get("title", ""),
                            caption=img_info.get("caption", ""),
                        )
                        if result.get("id"):
                            image_map[image_id] = {
                                "url": result["url"],
                                "media_id": result["id"],
                                "alt": result.get("alt", alt_text),
                            }
                            media_ids.append(result["id"])
                            is_eyecatch = img_info.get("eyecatch", False)
                            if is_eyecatch or (
                                featured_media_id is None and "eyecatch" in img_path.stem.lower()
                            ):
                                featured_media_id = result["id"]
                    if featured_media_id is None and media_ids:
                        featured_media_id = media_ids[0]

        # ── 3. article.html を読み込み、プレースホルダーを置換 ──
        article_file = draft_path / "article.html"
        if not article_file.exists():
            raise FileNotFoundError(f"article.html が見つかりません: {article_file}")

        with open(article_file, "r", encoding="utf-8") as f:
            content = f.read()

        content = _replace_image_placeholders(content, image_map)
        print(f"\n記事本文: {len(content)} 文字")

        # ── 4. カテゴリ・タグのID解決 ──
        category_ids = []
        if category_names:
            print(f"\nカテゴリ解決:")
            for name in category_names:
                cat_id = self.get_or_create_category(name)
                category_ids.append(cat_id)

        tag_ids = []
        if tag_names:
            print(f"\nタグ解決:")
            for name in tag_names:
                tag_id = self.get_or_create_tag(name)
                tag_ids.append(tag_id)

        # ── 5. 記事更新 ──
        print(f"\n更新処理:")
        post_result = self.update_post(
            post_id=post_id,
            content=content,
            title=title,
            featured_media_id=featured_media_id,
            categories=category_ids if category_ids else None,
            tags=tag_ids if tag_ids else None,
            meta=seo_meta if seo_meta else None,
            slug=slug,
        )

        result = {
            "post_id": post_result["id"],
            "edit_url": post_result["url"],
            "preview_url": post_result.get("preview_url", ""),
            "media_ids": media_ids,
        }

        print(f"\n{'='*60}")
        print(f"更新完了!")
        print(f"  記事ID: {result['post_id']}")
        print(f"  編集URL: {result['edit_url']}")
        print(f"{'='*60}")

        return result

    # ──────────────────────────────────────────
    # カテゴリ・タグ管理
    # ──────────────────────────────────────────

    def get_or_create_category(self, name: str) -> int:
        """
        カテゴリ名からIDを取得する。存在しなければ新規作成する。

        Args:
            name: カテゴリ名

        Returns:
            int: カテゴリID
        """
        # まず既存カテゴリを検索
        resp = self._get("/categories", params={"search": name, "per_page": 100})
        categories = resp.json()

        for cat in categories:
            if cat["name"].lower() == name.lower():
                print(f"  カテゴリ取得: 「{name}」 (ID: {cat['id']})")
                return cat["id"]

        # 見つからなければ作成
        resp = self._post("/categories", json={"name": name})
        new_cat = resp.json()
        print(f"  カテゴリ作成: 「{name}」 (ID: {new_cat['id']})")
        return new_cat["id"]

    def get_or_create_tag(self, name: str) -> int:
        """
        タグ名からIDを取得する。存在しなければ新規作成する。

        Args:
            name: タグ名

        Returns:
            int: タグID
        """
        # まず既存タグを検索
        resp = self._get("/tags", params={"search": name, "per_page": 100})
        tags = resp.json()

        for tag in tags:
            if tag["name"].lower() == name.lower():
                print(f"  タグ取得: 「{name}」 (ID: {tag['id']})")
                return tag["id"]

        # 見つからなければ作成
        resp = self._post("/tags", json={"name": name})
        new_tag = resp.json()
        print(f"  タグ作成: 「{name}」 (ID: {new_tag['id']})")
        return new_tag["id"]

    # ──────────────────────────────────────────
    # ディレクトリからの一括投稿
    # ──────────────────────────────────────────

    def publish_draft_from_dir(self, draft_dir: str) -> dict:
        """
        drafts/{slug}/ ディレクトリから一括で下書き投稿を行う。

        ディレクトリ構成:
            drafts/{slug}/
                article.html       - 記事本文（Gutenbergブロック形式）
                meta.json          - メタ情報（タイトル、カテゴリ等）
                images/            - アップロードする画像
                image_results.json - 画像生成結果（IDとファイル名のマッピング）

        処理手順:
            1. meta.json を読み込み
            2. images/ 内の画像をアップロード
            3. article.html を読み込み、画像プレースホルダーを実URLに置換
            4. カテゴリ・タグのID解決
            5. 下書き投稿

        Args:
            draft_dir: 下書きディレクトリのパス

        Returns:
            dict: {"post_id": ..., "edit_url": ..., "media_ids": [...]}
        """
        draft_path = Path(draft_dir)
        if not draft_path.is_dir():
            raise FileNotFoundError(f"下書きディレクトリが見つかりません: {draft_dir}")

        print(f"{'='*60}")
        print(f"下書き投稿開始: {draft_path.name}")
        print(f"{'='*60}")

        # ── 1. meta.json を読み込み ──
        meta_file = draft_path / "meta.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"meta.json が見つかりません: {meta_file}")

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        title = meta.get("title", draft_path.name)
        slug = meta.get("slug", "")
        category_names = meta.get("categories", [])
        tag_names = meta.get("tags", [])
        seo_meta = {}
        if "seo_title" in meta:
            seo_meta["_yoast_wpseo_title"] = meta["seo_title"]
        if "seo_description" in meta:
            seo_meta["_yoast_wpseo_metadesc"] = meta["seo_description"]
        if "focus_keyword" in meta:
            seo_meta["_yoast_wpseo_focuskw"] = meta["focus_keyword"]

        print(f"タイトル: {title}")

        # ── 2. 画像アップロード ──
        images_dir = draft_path / "images"
        image_map = {}  # image_id -> {"url": ..., "media_id": ...}
        media_ids = []
        featured_media_id = None

        # image_results.json がある場合はそこから画像IDとファイル名のマッピングを取得
        image_results_file = draft_path / "image_results.json"
        image_results = {}
        if image_results_file.exists():
            with open(image_results_file, "r", encoding="utf-8") as f:
                image_results = json.load(f)

        if images_dir.is_dir():
            image_files = sorted(
                p for p in images_dir.iterdir()
                if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
            )

            if image_files:
                print(f"\n画像アップロード（{len(image_files)}件）:")

                for img_path in image_files:
                    # image_results.json からマッピング情報を取得
                    img_info = _find_image_info(image_results, img_path.name)
                    alt_text = img_info.get("alt", "")
                    image_id = img_info.get("id", img_path.stem)

                    result = self.upload_media(
                        file_path=str(img_path),
                        alt_text=alt_text,
                        title=img_info.get("title", ""),
                        caption=img_info.get("caption", ""),
                    )

                    if result.get("id"):
                        image_map[image_id] = {
                            "url": result["url"],
                            "media_id": result["id"],
                            "alt": result.get("alt", alt_text),
                        }
                        media_ids.append(result["id"])

                        # 最初の画像またはeyecatch指定をアイキャッチにする
                        is_eyecatch = img_info.get("eyecatch", False)
                        if is_eyecatch or (featured_media_id is None and "eyecatch" in img_path.stem.lower()):
                            featured_media_id = result["id"]

                # アイキャッチが見つからなかった場合、最初の画像を使用
                if featured_media_id is None and media_ids:
                    featured_media_id = media_ids[0]

        # ── 3. article.html を読み込み、プレースホルダーを置換 ──
        article_file = draft_path / "article.html"
        if not article_file.exists():
            raise FileNotFoundError(f"article.html が見つかりません: {article_file}")

        with open(article_file, "r", encoding="utf-8") as f:
            content = f.read()

        # <!-- IMAGE: {image_id} --> 形式のプレースホルダーを置換
        content = _replace_image_placeholders(content, image_map)

        print(f"\n記事本文: {len(content)} 文字")

        # ── 4. カテゴリ・タグのID解決 ──
        category_ids = []
        if category_names:
            print(f"\nカテゴリ解決:")
            for name in category_names:
                cat_id = self.get_or_create_category(name)
                category_ids.append(cat_id)

        tag_ids = []
        if tag_names:
            print(f"\nタグ解決:")
            for name in tag_names:
                tag_id = self.get_or_create_tag(name)
                tag_ids.append(tag_id)

        # ── 5. 下書き投稿 ──
        print(f"\n投稿処理:")
        post_result = self.create_draft(
            title=title,
            content=content,
            featured_media_id=featured_media_id,
            categories=category_ids if category_ids else None,
            tags=tag_ids if tag_ids else None,
            meta=seo_meta if seo_meta else None,
            slug=slug if slug else None,
        )

        result = {
            "post_id": post_result["id"],
            "edit_url": post_result["url"],
            "preview_url": post_result.get("preview_url", ""),
            "media_ids": media_ids,
        }

        print(f"\n{'='*60}")
        print(f"投稿完了!")
        print(f"  記事ID: {result['post_id']}")
        print(f"  編集URL: {result['edit_url']}")
        print(f"  画像数: {len(media_ids)}")
        print(f"{'='*60}")

        return result


# ──────────────────────────────────────────────
# ユーティリティ関数
# ──────────────────────────────────────────────

def _find_image_info(image_results: dict, filename: str) -> dict:
    """
    image_results.json から画像ファイル名に対応する情報を検索する。

    新形式（image_client.py 出力）:
        {
            "eyecatch": {"path": "images/eyecatch.png", "alt": "..."},
            "illustrations": [{"id": "illust_1", "path": "images/illustration_1.png", "alt": "...", "caption": "..."}],
            "diagrams":      [{"id": "diagram_1",  "path": "images/diagram_1.png",  "alt": "...", "caption": "..."}]
        }

    旧形式（後方互換）:
        {
            "images": [{"id": "eyecatch", "filename": "eyecatch.png", "alt": "...", "eyecatch": true}, ...]
        }

    Args:
        image_results: image_results.json の内容（dict）
        filename: 検索するファイル名

    Returns:
        dict: 画像情報。見つからなければ空のdict
    """
    from pathlib import Path as _Path

    # ── 新形式: eyecatch ──
    eyecatch = image_results.get("eyecatch")
    if eyecatch and isinstance(eyecatch, dict):
        ec_path = eyecatch.get("path", "")
        if _Path(ec_path).name == filename or ec_path == filename:
            result = dict(eyecatch)
            result.setdefault("id", "eyecatch")
            result["eyecatch"] = True
            result["filename"] = filename
            return result

    # ── 新形式: illustrations / diagrams ──
    for key in ("illustrations", "diagrams", "screenshots"):
        items = image_results.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            item_path = item.get("path", "")
            # path のファイル名部分でマッチ
            if _Path(item_path).name == filename or item_path == filename:
                result = dict(item)
                result["filename"] = filename
                return result

    # ── 旧形式: images 配列 ──
    images = image_results.get("images", [])

    if isinstance(images, list):
        for img in images:
            if img.get("filename") == filename:
                return img
            # 拡張子なしのIDでもマッチ
            if img.get("id") and filename.startswith(img["id"]):
                return img

    # dict形式（キーがimage_id）の場合
    if isinstance(images, dict):
        for img_id, img_info in images.items():
            if img_info.get("filename") == filename:
                result = dict(img_info)
                result.setdefault("id", img_id)
                return result

    return {}


def _replace_image_placeholders(content: str, image_map: dict) -> str:
    """
    記事HTML内の画像プレースホルダーを実際の画像ブロックに置換する。

    プレースホルダー形式:
        <!-- IMAGE: {image_id} -->
        <!-- IMAGE: {image_id} alt="説明文" caption="キャプション" -->

    Args:
        content: 記事HTML
        image_map: image_id -> {"url": ..., "media_id": ..., "alt": ...} のマッピング

    Returns:
        str: 置換後の記事HTML
    """
    import re

    def replace_match(match):
        full_match = match.group(0)
        image_id = match.group(1).strip()
        attrs_str = match.group(2) or ""

        if image_id not in image_map:
            print(f"  [警告] 画像ID '{image_id}' のマッピングが見つかりません。"
                  f"プレースホルダーをそのまま残します。")
            return full_match

        img_data = image_map[image_id]
        url = img_data["url"]
        media_id = img_data.get("media_id", "")
        alt = img_data.get("alt", "")
        caption = ""

        # 属性文字列からalt, captionを抽出（プレースホルダー側の指定を優先）
        alt_match = re.search(r'alt="([^"]*)"', attrs_str)
        if alt_match:
            alt = alt_match.group(1)
        caption_match = re.search(r'caption="([^"]*)"', attrs_str)
        if caption_match:
            caption = caption_match.group(1)

        # Gutenberg画像ブロックを生成
        block_attrs = {"id": media_id} if media_id else {}
        attrs_json = json.dumps(block_attrs) if block_attrs else ""
        block_comment_open = f"<!-- wp:image {attrs_json} -->" if attrs_json else "<!-- wp:image -->"

        figure_class = f'wp-block-image'
        if media_id:
            figure_class += f' wp-image-{media_id}'

        img_tag = f'<img src="{url}" alt="{alt}" class="wp-image-{media_id}"/>' if media_id else f'<img src="{url}" alt="{alt}"/>'

        if caption:
            inner_html = (
                f'<figure class="{figure_class}">'
                f'{img_tag}'
                f'<figcaption class="wp-element-caption">{caption}</figcaption>'
                f'</figure>'
            )
        else:
            inner_html = (
                f'<figure class="{figure_class}">'
                f'{img_tag}'
                f'</figure>'
            )

        return f'{block_comment_open}\n{inner_html}\n<!-- /wp:image -->'

    # <!-- IMAGE: image_id --> 形式のプレースホルダーを検索・置換
    pattern = r'<!-- IMAGE:\s*(\S+)((?:\s+\w+="[^"]*")*)\s*-->'
    result = re.sub(pattern, replace_match, content)

    return result


# ──────────────────────────────────────────────
# CLI インターフェース
# ──────────────────────────────────────────────

def main():
    """コマンドラインからの実行エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="WordPress REST API クライアント",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python lib/wp_client.py --action check
  python lib/wp_client.py --action publish --draft-dir drafts/2026-02-22_test/
  python lib/wp_client.py --action update --post-id 763 --draft-dir drafts/2026-02-23_claude/
        """,
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["check", "publish", "update"],
        help="実行するアクション（check: 接続テスト, publish: 下書き投稿, update: 既存記事更新）",
    )
    parser.add_argument(
        "--draft-dir",
        help="下書きディレクトリのパス（publish/update時に必須）",
    )
    parser.add_argument(
        "--post-id",
        type=int,
        help="更新対象の記事ID（update時に必須）",
    )

    args = parser.parse_args()

    # 設定のバリデーション
    errors = validate_wp_config()
    if errors:
        print("[エラー] WordPress設定に問題があります:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    client = WordPressClient()

    if args.action == "check":
        # 接続・認証テスト
        print("=" * 60)
        print("WordPress 接続・認証テスト")
        print("=" * 60)

        print("\n1. REST API接続テスト:")
        if not client.check_connection():
            sys.exit(1)

        print("\n2. 認証テスト:")
        try:
            client.check_authentication()
        except WordPressAuthError as e:
            print(f"[NG] {e}")
            sys.exit(1)

        print("\n全テスト合格!")

    elif args.action == "publish":
        # 下書き投稿
        if not args.draft_dir:
            print("[エラー] --draft-dir を指定してください")
            sys.exit(1)

        draft_path = Path(args.draft_dir)
        # 相対パスの場合、DRAFTS_DIRからの相対パスとして解決
        if not draft_path.is_absolute():
            # まずカレントディレクトリからの相対パスを試す
            if not draft_path.is_dir():
                draft_path = DRAFTS_DIR / args.draft_dir
            if not draft_path.is_dir():
                print(f"[エラー] 下書きディレクトリが見つかりません: {args.draft_dir}")
                sys.exit(1)

        try:
            result = client.publish_draft_from_dir(str(draft_path))
            print(f"\n投稿成功! 編集URL: {result['edit_url']}")
        except (WordPressClientError, FileNotFoundError) as e:
            print(f"\n[エラー] 投稿に失敗しました: {e}")
            sys.exit(1)

    elif args.action == "update":
        # 既存記事の更新
        if not args.post_id:
            print("[エラー] --post-id を指定してください")
            sys.exit(1)
        if not args.draft_dir:
            print("[エラー] --draft-dir を指定してください")
            sys.exit(1)

        draft_path = Path(args.draft_dir)
        if not draft_path.is_absolute():
            if not draft_path.is_dir():
                draft_path = DRAFTS_DIR / args.draft_dir
            if not draft_path.is_dir():
                print(f"[エラー] 下書きディレクトリが見つかりません: {args.draft_dir}")
                sys.exit(1)

        try:
            result = client.update_post_from_dir(args.post_id, str(draft_path))
            print(f"\n更新成功! 編集URL: {result['edit_url']}")
        except (WordPressClientError, FileNotFoundError) as e:
            print(f"\n[エラー] 更新に失敗しました: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
