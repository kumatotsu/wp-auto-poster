# WordPress REST API 調査レポート

**対象サイト:** m-totsu.com（とつブログ）
**テーマ:** Cocoon（無料テーマ）
**SEOプラグイン:** Yoast SEO
**認証方式:** アプリケーションパスワード
**調査日:** 2026-02-21

---

## 目次

1. [認証（アプリケーションパスワード）](#1-認証アプリケーションパスワード)
2. [メディアアップロード（画像）](#2-メディアアップロード画像)
3. [下書き投稿（画像付き）](#3-下書き投稿画像付き)
4. [Yoast SEO メタデータ設定](#4-yoast-seo-メタデータ設定)
5. [Cocoonテーマ固有の注意点](#5-cocoonテーマ固有の注意点)
6. [完全なワークフローコード](#6-完全なワークフローコード)
7. [トラブルシューティング](#7-トラブルシューティング)

---

## 1. 認証（アプリケーションパスワード）

### 1.1 アプリケーションパスワードとは

WordPress 5.6以降に標準搭載された認証機能で、REST APIやXML-RPCへのアクセスに使用する専用パスワードを発行できる。通常のログインパスワードとは別に管理され、個別に無効化・削除が可能。

### 1.2 アプリケーションパスワードの生成手順

1. WordPress管理画面にログイン
2. **ユーザー** → **プロフィール** に移動
3. ページ下部の **「アプリケーションパスワード」** セクションを見つける
4. **「新しいアプリケーションパスワードの名前」** に識別用の名前を入力（例: `Python自動投稿`）
5. **「新しいアプリケーションパスワードを追加」** をクリック
6. 表示されるパスワードを**その場でコピーして安全に保管**（再表示不可）

> **注意:** アプリケーションパスワードはスペース区切りで表示されるが、使用時にスペースを含めても除去しても動作する。

### 1.3 前提条件

- サイトが **HTTPS** で運用されていること（HTTPの場合はアプリケーションパスワードが無効化される場合がある）
- m-totsu.com がHTTPS対応であれば問題なし

### 1.4 Basic認証の実装（Python）

```python
import requests
import base64

# 認証情報
WP_URL = "https://m-totsu.com"
WP_USER = "あなたのユーザー名"
WP_APP_PASSWORD = "xxxx xxxx xxxx xxxx xxxx xxxx"  # アプリケーションパスワード

# requests ライブラリでの Basic 認証（方法1: 推奨）
# requests は auth パラメータで自動的にBase64エンコードする
auth = (WP_USER, WP_APP_PASSWORD)

response = requests.get(
    f"{WP_URL}/wp-json/wp/v2/posts",
    auth=auth
)
print(response.status_code)
```

```python
# 方法2: 手動でAuthorizationヘッダーを設定する場合
import base64

credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
token = base64.b64encode(credentials.encode()).decode("utf-8")

headers = {
    "Authorization": f"Basic {token}"
}

response = requests.get(
    f"{WP_URL}/wp-json/wp/v2/posts",
    headers=headers
)
```

### 1.5 セキュリティベストプラクティス

| 項目 | 推奨事項 |
|------|----------|
| HTTPS必須 | 必ずHTTPS経由でAPIにアクセスする。HTTPではBasic認証の資格情報が平文で送信される |
| パスワード管理 | アプリケーションパスワードは環境変数や `.env` ファイルで管理し、コードにハードコードしない |
| 最小権限 | API用のユーザーアカウントを作成し、必要最小限の権限（投稿者/編集者）のみ付与する |
| パスワードのローテーション | 定期的にアプリケーションパスワードを再発行する |
| 不使用時の無効化 | 使用しなくなったアプリケーションパスワードは管理画面から削除する |
| IPアドレス制限 | 可能であれば、サーバー側で API アクセスを特定IPに制限する |
| ログ監視 | セキュリティプラグインでAPIアクセスのログを監視する |

```python
# .env ファイルでの認証情報管理（推奨）
# .env ファイル:
# WP_USER=your_username
# WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

import os
from dotenv import load_dotenv

load_dotenv()

WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
```

---

## 2. メディアアップロード（画像）

### 2.1 エンドポイント仕様

| 項目 | 詳細 |
|------|------|
| **エンドポイント** | `POST /wp-json/wp/v2/media` |
| **認証** | 必須（`upload_files` 権限が必要） |
| **Content-Type** | 画像のMIMEタイプ（例: `image/jpeg`, `image/png`） |
| **必須ヘッダー** | `Content-Disposition: attachment; filename="ファイル名"` |

### 2.2 リクエストパラメータ

画像アップロードは2段階で行う方法が確実:

**ステップ1: 画像バイナリのアップロード**

| ヘッダー | 値 | 説明 |
|---------|---|------|
| `Content-Type` | `image/jpeg` 等 | 画像のMIMEタイプ |
| `Content-Disposition` | `attachment; filename="example.jpg"` | ファイル名指定 |

**ステップ2: メタデータの更新（POST /wp-json/wp/v2/media/{id}）**

| パラメータ | 型 | 説明 |
|-----------|---|------|
| `title` | object | メディアのタイトル（`{"raw": "タイトル"}` または文字列） |
| `alt_text` | string | 代替テキスト（SEOに重要） |
| `caption` | object | キャプション（`{"raw": "キャプション"}` または文字列） |
| `description` | object | 説明（`{"raw": "説明"}` または文字列） |
| `post` | integer | 関連付ける投稿ID |
| `status` | string | `inherit`（デフォルト）、`private`、`trash` |

### 2.3 対応画像形式とサイズ制限

**対応画像形式（デフォルト）:**

| 形式 | MIMEタイプ | 拡張子 |
|------|-----------|--------|
| JPEG | `image/jpeg` | `.jpg`, `.jpeg` |
| PNG | `image/png` | `.png` |
| GIF | `image/gif` | `.gif` |
| WebP | `image/webp` | `.webp`（WordPress 5.8以降） |
| AVIF | `image/avif` | `.avif`（WordPress 6.5以降） |
| ICO | `image/x-icon` | `.ico` |
| BMP | `image/bmp` | `.bmp` |
| TIFF | `image/tiff` | `.tiff`, `.tif` |
| SVG | ※デフォルトでは非対応 | プラグインで対応可 |

**サイズ制限:**

| 制限項目 | デフォルト値 | 設定場所 |
|---------|------------|---------|
| 最大アップロードサイズ | サーバー依存（一般的に2MB〜128MB） | `php.ini` の `upload_max_filesize` |
| POST最大サイズ | サーバー依存 | `php.ini` の `post_max_size` |
| WordPress側制限 | サーバー設定に準拠 | `wp-config.php` で変更可 |

> **確認方法:** 管理画面の **メディア** → **新しいメディアファイルを追加** で「最大アップロードサイズ」が表示される。

### 2.4 Pythonによる画像アップロードコード

```python
import requests
import os
import mimetypes

WP_URL = "https://m-totsu.com"
auth = (WP_USER, WP_APP_PASSWORD)

def upload_image(file_path, title=None, alt_text=None, caption=None):
    """
    画像をWordPressメディアライブラリにアップロードする

    Args:
        file_path: アップロードする画像ファイルのパス
        title: メディアタイトル（省略時はファイル名）
        alt_text: 代替テキスト
        caption: キャプション

    Returns:
        dict: アップロードされたメディアの情報（id, source_url等）
    """

    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type is None:
        mime_type = "application/octet-stream"

    # 画像ファイルをバイナリモードで読み込み
    with open(file_path, "rb") as f:
        file_data = f.read()

    # ヘッダー設定
    headers = {
        "Content-Type": mime_type,
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }

    # アップロードリクエスト
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        headers=headers,
        data=file_data,
        auth=auth,
    )

    if response.status_code != 201:
        raise Exception(f"アップロード失敗: {response.status_code} - {response.text}")

    media = response.json()
    media_id = media["id"]

    # メタデータの更新（alt_text, title, caption）
    meta_data = {}
    if title:
        meta_data["title"] = title
    if alt_text:
        meta_data["alt_text"] = alt_text
    if caption:
        meta_data["caption"] = caption

    if meta_data:
        meta_response = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
            json=meta_data,
            auth=auth,
        )
        if meta_response.status_code == 200:
            media = meta_response.json()

    return media


# 使用例
media = upload_image(
    file_path="/path/to/image.jpg",
    title="サンプル画像",
    alt_text="サンプル画像の説明テキスト",
    caption="これはキャプションです"
)

print(f"Media ID: {media['id']}")
print(f"URL: {media['source_url']}")
```

### 2.5 アップロードレスポンスの構造

```json
{
    "id": 1234,
    "date": "2026-02-21T12:00:00",
    "slug": "sample-image",
    "status": "inherit",
    "type": "attachment",
    "title": {
        "rendered": "サンプル画像"
    },
    "author": 1,
    "description": {
        "rendered": "<p>説明</p>"
    },
    "caption": {
        "rendered": "<p>キャプション</p>"
    },
    "alt_text": "代替テキスト",
    "media_type": "image",
    "mime_type": "image/jpeg",
    "source_url": "https://m-totsu.com/wp-content/uploads/2026/02/sample-image.jpg",
    "media_details": {
        "width": 1920,
        "height": 1080,
        "file": "2026/02/sample-image.jpg",
        "sizes": {
            "thumbnail": {
                "file": "sample-image-150x150.jpg",
                "width": 150,
                "height": 150,
                "source_url": "https://m-totsu.com/wp-content/uploads/2026/02/sample-image-150x150.jpg"
            },
            "medium": {
                "file": "sample-image-300x169.jpg",
                "width": 300,
                "height": 169,
                "source_url": "https://m-totsu.com/wp-content/uploads/2026/02/sample-image-300x169.jpg"
            },
            "large": {
                "file": "sample-image-1024x576.jpg",
                "width": 1024,
                "height": 576,
                "source_url": "https://m-totsu.com/wp-content/uploads/2026/02/sample-image-1024x576.jpg"
            },
            "full": {
                "file": "sample-image.jpg",
                "width": 1920,
                "height": 1080,
                "source_url": "https://m-totsu.com/wp-content/uploads/2026/02/sample-image.jpg"
            }
        }
    }
}
```

**よく使うレスポンスフィールド:**

| フィールド | 説明 |
|-----------|------|
| `id` | メディアID（`featured_media` に使用） |
| `source_url` | 元画像のフルURL |
| `media_details.sizes.{size}.source_url` | 各サイズの画像URL |
| `alt_text` | 設定された代替テキスト |
| `title.rendered` | レンダリング済みタイトル |

---

## 3. 下書き投稿（画像付き）

### 3.1 エンドポイント仕様

| 項目 | 詳細 |
|------|------|
| **エンドポイント** | `POST /wp-json/wp/v2/posts` |
| **認証** | 必須（`edit_posts` 権限が必要） |
| **Content-Type** | `application/json` |

### 3.2 主要リクエストパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|---|-----------|------|
| `title` | string | - | 投稿タイトル |
| `content` | string | - | 投稿本文（HTMLまたはブロックエディタ形式） |
| `status` | string | `draft` | 投稿ステータス: `draft`, `publish`, `pending`, `private`, `future` |
| `featured_media` | integer | 0 | アイキャッチ画像のメディアID |
| `categories` | array[int] | - | カテゴリIDの配列 |
| `tags` | array[int] | - | タグIDの配列 |
| `excerpt` | string | - | 抜粋 |
| `slug` | string | 自動生成 | URLスラッグ |
| `date` | string | 現在時刻 | 投稿日時（ISO8601形式） |
| `author` | integer | 認証ユーザー | 著者ユーザーID |
| `comment_status` | string | - | `open` または `closed` |
| `ping_status` | string | - | `open` または `closed` |
| `meta` | object | - | カスタムフィールド（プラグインの拡張含む） |
| `format` | string | `standard` | 投稿フォーマット |

### 3.3 アイキャッチ画像（featured_media）の設定

```python
def create_draft_post(title, content, featured_media_id=None, categories=None, tags=None):
    """
    下書き投稿を作成する

    Args:
        title: 投稿タイトル
        content: 投稿本文（HTML）
        featured_media_id: アイキャッチ画像のメディアID
        categories: カテゴリIDのリスト
        tags: タグIDのリスト

    Returns:
        dict: 作成された投稿の情報
    """

    post_data = {
        "title": title,
        "content": content,
        "status": "draft",  # 下書きとして保存
    }

    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    if categories:
        post_data["categories"] = categories

    if tags:
        post_data["tags"] = tags

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        json=post_data,
        auth=auth,
    )

    if response.status_code != 201:
        raise Exception(f"投稿作成失敗: {response.status_code} - {response.text}")

    return response.json()
```

### 3.4 記事本文中に画像を埋め込む方法

#### 方法1: WordPress ブロックエディタ（Gutenberg）形式（推奨）

Gutenbergブロック形式はHTMLコメントでブロックの境界を定義する。REST APIで投稿する場合もこの形式を使うことで、エディタでの編集互換性が保たれる。

```python
def create_image_block(image_url, image_id, alt_text="", caption="",
                        align="", size_slug="large", link_dest="none"):
    """
    WordPress画像ブロック（wp:image）のHTML文字列を生成する

    Args:
        image_url: 画像のURL
        image_id: メディアID
        alt_text: 代替テキスト
        caption: キャプション（空文字の場合はキャプション要素を省略）
        align: 配置（"", "left", "center", "right", "wide", "full"）
        size_slug: サイズ（"thumbnail", "medium", "large", "full"）
        link_dest: リンク先（"none", "media", "attachment"）

    Returns:
        str: Gutenbergブロック形式のHTML文字列
    """

    # ブロック属性のJSON
    block_attrs = {
        "id": image_id,
        "sizeSlug": size_slug,
        "linkDestination": link_dest,
    }
    if align:
        block_attrs["align"] = align

    import json
    attrs_json = json.dumps(block_attrs, ensure_ascii=False)

    # 配置クラス
    align_class = f" align{align}" if align else ""
    figure_class = f"wp-block-image size-{size_slug}{align_class}"

    # キャプション部分
    caption_html = f"<figcaption class=\"wp-element-caption\">{caption}</figcaption>" if caption else ""

    block = f"""<!-- wp:image {attrs_json} -->
<figure class="{figure_class}"><img src="{image_url}" alt="{alt_text}" class="wp-image-{image_id}"/>{caption_html}</figure>
<!-- /wp:image -->"""

    return block


def create_paragraph_block(text):
    """
    WordPress段落ブロック（wp:paragraph）のHTML文字列を生成する
    """
    return f"""<!-- wp:paragraph -->
<p>{text}</p>
<!-- /wp:paragraph -->"""


def create_heading_block(text, level=2):
    """
    WordPress見出しブロック（wp:heading）のHTML文字列を生成する
    """
    attrs = f' {{"level":{level}}}' if level != 2 else ""
    return f"""<!-- wp:heading{attrs} -->
<h{level} class="wp-block-heading">{text}</h{level}>
<!-- /wp:heading -->"""
```

**ブロック形式の記事本文の組み立て例:**

```python
content_blocks = []

# 導入文
content_blocks.append(create_paragraph_block(
    "この記事では、WordPress REST APIを使った自動投稿について解説します。"
))

# 見出し
content_blocks.append(create_heading_block("画像付き記事の作成", level=2))

# 本文
content_blocks.append(create_paragraph_block(
    "以下の画像は、REST APIを通じてアップロードしました。"
))

# 画像ブロック
content_blocks.append(create_image_block(
    image_url="https://m-totsu.com/wp-content/uploads/2026/02/sample.jpg",
    image_id=1234,
    alt_text="サンプル画像",
    caption="REST APIでアップロードした画像",
    size_slug="large",
))

# 追加の本文
content_blocks.append(create_paragraph_block(
    "このように、プログラムから画像付きの記事を投稿できます。"
))

# ブロックを改行2つで結合
content = "\n\n".join(content_blocks)
```

#### 方法2: 素のHTML形式

ブロックコメントを使わずにHTMLだけで記述する方法。エディタで開くと「クラシック」ブロックとして認識される。

```python
content = """
<p>この記事では画像を埋め込んでいます。</p>

<figure class="wp-block-image size-large">
    <img src="https://m-totsu.com/wp-content/uploads/2026/02/sample.jpg"
         alt="サンプル画像" />
    <figcaption>画像のキャプション</figcaption>
</figure>

<p>記事の続きです。</p>
"""
```

> **推奨:** 方法1のブロックエディタ形式を使うこと。Cocoonテーマのスタイリングがブロック形式に最適化されており、後からエディタで編集する際にも問題が起きにくい。

### 3.5 カテゴリ・タグIDの取得方法

```python
def get_categories():
    """カテゴリ一覧を取得"""
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories",
        params={"per_page": 100},
        auth=auth,
    )
    return response.json()

def get_tags():
    """タグ一覧を取得"""
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/tags",
        params={"per_page": 100},
        auth=auth,
    )
    return response.json()

def find_or_create_tag(tag_name):
    """タグを検索し、存在しなければ作成する"""
    # 既存タグを検索
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/tags",
        params={"search": tag_name},
        auth=auth,
    )
    tags = response.json()

    for tag in tags:
        if tag["name"].lower() == tag_name.lower():
            return tag["id"]

    # 存在しなければ作成
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/tags",
        json={"name": tag_name},
        auth=auth,
    )
    if response.status_code == 201:
        return response.json()["id"]

    raise Exception(f"タグ作成失敗: {response.text}")
```

---

## 4. Yoast SEO メタデータ設定

### 4.1 概要

Yoast SEOプラグインはWordPress REST APIを拡張し、投稿エンドポイントのレスポンスに `yoast_head_json` フィールドを追加する。また、投稿の作成・更新時に `meta` フィールドを通じてSEOメタデータを設定できる。

### 4.2 Yoast SEO が追加するREST APIフィールド

Yoast SEO v14以降では、投稿のレスポンスに以下が追加される:

```json
{
    "yoast_head": "<title>SEOタイトル</title><meta name=\"description\"...>",
    "yoast_head_json": {
        "title": "SEOタイトル - とつブログ",
        "description": "メタディスクリプション",
        "robots": {
            "index": "index",
            "follow": "follow"
        },
        "og_title": "OGPタイトル",
        "og_description": "OGP説明",
        "og_image": [
            {
                "url": "https://m-totsu.com/wp-content/uploads/...",
                "width": 1200,
                "height": 630
            }
        ],
        "twitter_card": "summary_large_image"
    }
}
```

### 4.3 Yoast SEO メタデータの設定方法

投稿の作成・更新時に `yoast_meta` または `meta` フィールドでSEO情報を設定する。

**方法1: `meta` フィールド経由（推奨）**

```python
post_data = {
    "title": "記事タイトル",
    "content": "記事本文...",
    "status": "draft",
    "featured_media": 1234,
    "meta": {
        "_yoast_wpseo_title": "%%title%% %%page%% %%sep%% %%sitename%%",
        "_yoast_wpseo_metadesc": "この記事のメタディスクリプション。検索結果に表示される説明文です。",
        "_yoast_wpseo_focuskw": "フォーカスキーワード",
        "_yoast_wpseo_canonical": "",  # カノニカルURL（通常は空でOK）
        "_yoast_wpseo_opengraph-title": "OGPタイトル（SNS共有時のタイトル）",
        "_yoast_wpseo_opengraph-description": "OGP説明文",
        "_yoast_wpseo_twitter-title": "Twitterカードタイトル",
        "_yoast_wpseo_twitter-description": "Twitterカード説明文",
    }
}

response = requests.post(
    f"{WP_URL}/wp-json/wp/v2/posts",
    json=post_data,
    auth=auth,
)
```

**方法2: `yoast_meta` フィールド経由**

Yoast SEOのバージョンによっては、トップレベルの `yoast_meta` フィールドが使える場合がある:

```python
post_data = {
    "title": "記事タイトル",
    "content": "記事本文...",
    "status": "draft",
    "yoast_meta": {
        "yoast_wpseo_title": "SEOタイトル",
        "yoast_wpseo_metadesc": "メタディスクリプション",
        "yoast_wpseo_focuskw": "フォーカスキーワード",
    }
}
```

### 4.4 Yoast SEO の主要メタフィールド一覧

| メタキー | 説明 | 例 |
|---------|------|---|
| `_yoast_wpseo_title` | SEOタイトル（テンプレート変数使用可） | `%%title%% %%sep%% %%sitename%%` |
| `_yoast_wpseo_metadesc` | メタディスクリプション | 120〜160文字推奨 |
| `_yoast_wpseo_focuskw` | フォーカスキーワード | メインキーワード |
| `_yoast_wpseo_canonical` | カノニカルURL | 通常は空（自動設定） |
| `_yoast_wpseo_opengraph-title` | OGP タイトル | SNS共有時のタイトル |
| `_yoast_wpseo_opengraph-description` | OGP 説明 | SNS共有時の説明文 |
| `_yoast_wpseo_opengraph-image` | OGP 画像URL | SNS共有時の画像 |
| `_yoast_wpseo_twitter-title` | Twitter タイトル | Twitterカード用 |
| `_yoast_wpseo_twitter-description` | Twitter 説明 | Twitterカード用 |
| `_yoast_wpseo_meta-robots-noindex` | noindex設定 | `1` = noindex |
| `_yoast_wpseo_meta-robots-nofollow` | nofollow設定 | `1` = nofollow |
| `_yoast_wpseo_schema_page_type` | Schema.orgページタイプ | `WebPage`, `FAQPage` 等 |
| `_yoast_wpseo_schema_article_type` | Schema.org記事タイプ | `Article`, `BlogPosting` 等 |

### 4.5 Yoast SEO テンプレート変数

SEOタイトルでは以下のテンプレート変数が使用可能:

| 変数 | 展開される値 |
|------|------------|
| `%%title%%` | 投稿タイトル |
| `%%sitename%%` | サイト名 |
| `%%sep%%` | セパレータ（通常は `-` や `\|`） |
| `%%page%%` | ページ番号 |
| `%%excerpt%%` | 抜粋 |
| `%%date%%` | 投稿日 |
| `%%category%%` | 最初のカテゴリ名 |
| `%%tag%%` | 最初のタグ名 |
| `%%primary_category%%` | プライマリカテゴリ名 |

### 4.6 注意事項

- `meta` フィールドを使ってYoastのメタデータを設定するには、REST APIでカスタムフィールドの登録が有効になっている必要がある。Yoast SEOプラグインが有効であれば通常は自動的に登録される。
- 一部のメタフィールドはWordPressの `register_meta()` で `show_in_rest` が `true` に設定されていないと REST API 経由で書き込めない場合がある。その場合は、以下のようなカスタムプラグインまたは `functions.php` への追記が必要になることがある:

```php
// functions.php に追記（必要な場合のみ）
add_action('init', function() {
    $meta_keys = [
        '_yoast_wpseo_title',
        '_yoast_wpseo_metadesc',
        '_yoast_wpseo_focuskw',
        '_yoast_wpseo_opengraph-title',
        '_yoast_wpseo_opengraph-description',
        '_yoast_wpseo_twitter-title',
        '_yoast_wpseo_twitter-description',
    ];

    foreach ($meta_keys as $key) {
        register_meta('post', $key, [
            'show_in_rest' => true,
            'single' => true,
            'type' => 'string',
            'auth_callback' => function() {
                return current_user_can('edit_posts');
            },
        ]);
    }
});
```

---

## 5. Cocoonテーマ固有の注意点

### 5.1 Cocoonテーマのカスタムフィールド

Cocoonテーマは独自のカスタムフィールド（post_meta）を多数使用している。REST API経由で設定する場合は `meta` フィールドで指定する。

**主要なCocoonカスタムフィールド:**

| メタキー | 説明 | 値 |
|---------|------|---|
| `the_page_eye_catch` | アイキャッチ画像URL（テーマ独自） | URL文字列 |
| `the_page_seo_title` | Cocoon独自SEOタイトル | 文字列 |
| `the_page_meta_description` | Cocoon独自メタディスクリプション | 文字列 |
| `the_page_meta_keywords` | メタキーワード | カンマ区切り文字列 |
| `the_page_noindex` | noindex設定 | `1` = noindex |
| `the_page_nofollow` | nofollow設定 | `1` = nofollow |

> **重要:** Yoast SEOを使用している場合、CocoonのSEO設定よりもYoast SEOの設定が優先されるのが一般的。SEOメタデータはYoast SEO側で設定すること。

### 5.2 Cocoonテーマでの注意事項

1. **アイキャッチ画像:** CocoonテーマはWordPress標準の `featured_media` をアイキャッチ画像として使用する。REST APIで `featured_media` にメディアIDを設定すれば、Cocoonのアイキャッチとして正しく反映される。

2. **画像の遅延読み込み（Lazy Load）:** Cocoonはデフォルトで画像の遅延読み込みを有効にしている。REST APIで投稿した画像も自動的にLazy Loadが適用される（テーマ側のフィルターで処理される）。

3. **目次の自動生成:** Cocoonは見出しタグ（h2〜h4）から目次を自動生成する。REST APIで投稿する際もGutenbergの見出しブロック（`<!-- wp:heading -->`）を使えば、目次が自動生成される。

4. **吹き出し（Speech Bubble）:** Cocoonの吹き出し機能はショートコードまたはブロックで実装されている。REST APIで使う場合:

```python
# Cocoonの吹き出しブロック
speech_bubble = """<!-- wp:cocoon-blocks/balloon-ex-box {"balloonId":1} -->
<div class="wp-block-cocoon-blocks-balloon-ex-box speech-wrap sb-id-1 sbs-line sbp-l sbis-sn cf">
<div class="speech-person"><img src="アバターURL" alt="名前" class="speech-icon-image"/><span class="speech-name">名前</span></div>
<div class="speech-balloon"><p>吹き出しのテキスト</p></div>
</div>
<!-- /wp:cocoon-blocks/balloon-ex-box -->"""
```

5. **ブログカード:** Cocoonの内部リンク・外部リンクのブログカード機能を使うには:

```python
# Cocoonのブログカード（URLを貼るだけで自動変換）
blog_card = """<!-- wp:embed {"url":"https://example.com/article","type":"rich"} -->
<figure class="wp-block-embed is-type-rich"><div class="wp-block-embed__wrapper">
https://example.com/article
</div></figure>
<!-- /wp:embed -->"""
```

6. **広告設定:** Cocoonの広告挿入ポジションは管理画面の「Cocoon設定」から行い、REST API経由では制御しない。

7. **画像サイズ:** Cocoonテーマは独自の画像サイズを追加登録している場合がある。`media_details.sizes` にCocoon固有のサイズが含まれることがある。

### 5.3 REST API でカスタムフィールドを使用するための設定

CocoonのカスタムフィールドをREST API経由で設定するには、`functions.php` での登録が必要な場合がある:

```php
// Cocoon子テーマの functions.php に追記
add_action('init', function() {
    // REST API でカスタムフィールドを使用可能にする
    register_meta('post', 'the_page_meta_description', [
        'show_in_rest' => true,
        'single' => true,
        'type' => 'string',
    ]);
    // 必要に応じて他のメタキーも追加
});
```

> **ただし、Yoast SEOを併用している場合は、Cocoon独自のSEOフィールドではなくYoast SEOのフィールドを使用するのが推奨。** 重複すると予期しない動作になる可能性がある。

---

## 6. 完全なワークフローコード

以下は、画像をアップロードし、アイキャッチ画像と本文中の画像を含む下書き記事を投稿する完全なPythonコード。

### 6.1 必要なライブラリのインストール

```bash
pip install requests python-dotenv
```

### 6.2 .env ファイルの準備

```env
# .env
WP_URL=https://m-totsu.com
WP_USER=あなたのユーザー名
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

### 6.3 完全なワークフローコード

```python
#!/usr/bin/env python3
"""
WordPress REST API 自動投稿スクリプト
- 画像アップロード
- アイキャッチ画像設定
- 本文中の画像埋め込み（Gutenbergブロック形式）
- Yoast SEO メタデータ設定
- 下書き投稿の作成
"""

import os
import json
import mimetypes
import requests
from dotenv import load_dotenv


# ============================================================
# 設定
# ============================================================

load_dotenv()

WP_URL = os.getenv("WP_URL", "https://m-totsu.com")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# Basic認証タプル
AUTH = (WP_USER, WP_APP_PASSWORD)

# APIのベースURL
API_BASE = f"{WP_URL}/wp-json/wp/v2"


# ============================================================
# ユーティリティ関数
# ============================================================

def check_connection():
    """API接続確認"""
    try:
        response = requests.get(f"{WP_URL}/wp-json/", timeout=10)
        if response.status_code == 200:
            site_info = response.json()
            print(f"[OK] サイト接続成功: {site_info.get('name', 'Unknown')}")
            return True
        else:
            print(f"[ERROR] 接続失敗: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 接続エラー: {e}")
        return False


def check_authentication():
    """認証確認"""
    response = requests.get(
        f"{API_BASE}/users/me",
        auth=AUTH,
        timeout=10,
    )
    if response.status_code == 200:
        user = response.json()
        print(f"[OK] 認証成功: {user['name']} (ID: {user['id']})")
        return True
    else:
        print(f"[ERROR] 認証失敗: HTTP {response.status_code}")
        print(f"  レスポンス: {response.text[:200]}")
        return False


# ============================================================
# メディア（画像）アップロード
# ============================================================

def upload_image(file_path, title=None, alt_text=None, caption=None, description=None):
    """
    画像をWordPressメディアライブラリにアップロードする

    Args:
        file_path (str): アップロードする画像ファイルのローカルパス
        title (str): メディアタイトル（省略時はファイル名から自動設定）
        alt_text (str): 代替テキスト（SEOに重要）
        caption (str): キャプション
        description (str): 説明

    Returns:
        dict: アップロードされたメディア情報 {id, source_url, media_details, ...}

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        Exception: アップロードに失敗した場合
    """
    # ファイルの存在確認
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type is None:
        mime_type = "application/octet-stream"

    # 対応MIMEタイプの確認
    supported_types = [
        "image/jpeg", "image/png", "image/gif",
        "image/webp", "image/avif", "image/bmp",
        "image/tiff", "image/x-icon",
    ]
    if mime_type not in supported_types:
        print(f"[WARN] MIMEタイプ '{mime_type}' はサポートされていない可能性があります")

    file_size = os.path.getsize(file_path)
    print(f"[INFO] アップロード開始: {file_name} ({mime_type}, {file_size:,} bytes)")

    # 画像データを読み込み
    with open(file_path, "rb") as f:
        file_data = f.read()

    # アップロードリクエスト
    headers = {
        "Content-Type": mime_type,
        "Content-Disposition": f'attachment; filename="{file_name}"',
    }

    response = requests.post(
        f"{API_BASE}/media",
        headers=headers,
        data=file_data,
        auth=AUTH,
        timeout=60,  # 大きな画像の場合を考慮
    )

    if response.status_code != 201:
        raise Exception(
            f"画像アップロード失敗: HTTP {response.status_code}\n"
            f"レスポンス: {response.text[:500]}"
        )

    media = response.json()
    media_id = media["id"]
    print(f"[OK] アップロード成功: ID={media_id}")

    # メタデータの更新
    meta_update = {}
    if title:
        meta_update["title"] = title
    if alt_text:
        meta_update["alt_text"] = alt_text
    if caption:
        meta_update["caption"] = caption
    if description:
        meta_update["description"] = description

    if meta_update:
        meta_response = requests.post(
            f"{API_BASE}/media/{media_id}",
            json=meta_update,
            auth=AUTH,
            timeout=30,
        )
        if meta_response.status_code == 200:
            media = meta_response.json()
            print(f"[OK] メタデータ更新成功")
        else:
            print(f"[WARN] メタデータ更新失敗: HTTP {meta_response.status_code}")

    # 結果の表示
    print(f"  - Media ID: {media['id']}")
    print(f"  - URL: {media['source_url']}")
    if "media_details" in media and "sizes" in media["media_details"]:
        sizes = media["media_details"]["sizes"]
        print(f"  - 利用可能サイズ: {', '.join(sizes.keys())}")

    return media


# ============================================================
# Gutenbergブロック生成ヘルパー
# ============================================================

def block_image(image_url, image_id, alt_text="", caption="",
                align="", size_slug="large", link_dest="none"):
    """WordPress画像ブロック（wp:image）を生成"""
    block_attrs = {
        "id": image_id,
        "sizeSlug": size_slug,
        "linkDestination": link_dest,
    }
    if align:
        block_attrs["align"] = align

    attrs_json = json.dumps(block_attrs, ensure_ascii=False)
    align_class = f" align{align}" if align else ""
    figure_class = f"wp-block-image size-{size_slug}{align_class}"
    caption_html = (
        f'<figcaption class="wp-element-caption">{caption}</figcaption>'
        if caption else ""
    )

    return (
        f'<!-- wp:image {attrs_json} -->\n'
        f'<figure class="{figure_class}">'
        f'<img src="{image_url}" alt="{alt_text}" class="wp-image-{image_id}"/>'
        f'{caption_html}</figure>\n'
        f'<!-- /wp:image -->'
    )


def block_paragraph(text):
    """WordPress段落ブロック（wp:paragraph）を生成"""
    return (
        f'<!-- wp:paragraph -->\n'
        f'<p>{text}</p>\n'
        f'<!-- /wp:paragraph -->'
    )


def block_heading(text, level=2):
    """WordPress見出しブロック（wp:heading）を生成"""
    attrs = f' {{"level":{level}}}' if level != 2 else ""
    return (
        f'<!-- wp:heading{attrs} -->\n'
        f'<h{level} class="wp-block-heading">{text}</h{level}>\n'
        f'<!-- /wp:heading -->'
    )


def block_list(items, ordered=False):
    """WordPressリストブロック（wp:list）を生成"""
    tag = "ol" if ordered else "ul"
    attrs = ' {"ordered":true}' if ordered else ""
    items_html = "".join(f"<li>{item}</li>" for item in items)
    return (
        f'<!-- wp:list{attrs} -->\n'
        f'<{tag} class="wp-block-list">{items_html}</{tag}>\n'
        f'<!-- /wp:list -->'
    )


def block_quote(text, citation=""):
    """WordPress引用ブロック（wp:quote）を生成"""
    cite_html = f"<cite>{citation}</cite>" if citation else ""
    return (
        f'<!-- wp:quote -->\n'
        f'<blockquote class="wp-block-quote"><p>{text}</p>{cite_html}</blockquote>\n'
        f'<!-- /wp:quote -->'
    )


def build_content(blocks):
    """ブロックのリストを結合して記事本文を生成"""
    return "\n\n".join(blocks)


# ============================================================
# 投稿作成
# ============================================================

def create_draft_post(
    title,
    content,
    featured_media_id=None,
    categories=None,
    tags=None,
    excerpt=None,
    slug=None,
    yoast_title=None,
    yoast_metadesc=None,
    yoast_focuskw=None,
    yoast_og_title=None,
    yoast_og_description=None,
):
    """
    下書き投稿を作成する

    Args:
        title (str): 投稿タイトル
        content (str): 投稿本文（Gutenbergブロック形式のHTML）
        featured_media_id (int): アイキャッチ画像のメディアID
        categories (list[int]): カテゴリIDのリスト
        tags (list[int]): タグIDのリスト
        excerpt (str): 抜粋
        slug (str): URLスラッグ
        yoast_title (str): Yoast SEOタイトル
        yoast_metadesc (str): Yoast メタディスクリプション
        yoast_focuskw (str): Yoast フォーカスキーワード
        yoast_og_title (str): Yoast OGPタイトル
        yoast_og_description (str): Yoast OGP説明

    Returns:
        dict: 作成された投稿情報 {id, link, status, ...}

    Raises:
        Exception: 投稿作成に失敗した場合
    """

    post_data = {
        "title": title,
        "content": content,
        "status": "draft",
    }

    # オプションパラメータ
    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    if categories:
        post_data["categories"] = categories

    if tags:
        post_data["tags"] = tags

    if excerpt:
        post_data["excerpt"] = excerpt

    if slug:
        post_data["slug"] = slug

    # Yoast SEO メタデータ
    meta = {}
    if yoast_title:
        meta["_yoast_wpseo_title"] = yoast_title
    if yoast_metadesc:
        meta["_yoast_wpseo_metadesc"] = yoast_metadesc
    if yoast_focuskw:
        meta["_yoast_wpseo_focuskw"] = yoast_focuskw
    if yoast_og_title:
        meta["_yoast_wpseo_opengraph-title"] = yoast_og_title
    if yoast_og_description:
        meta["_yoast_wpseo_opengraph-description"] = yoast_og_description

    if meta:
        post_data["meta"] = meta

    print(f"[INFO] 下書き投稿作成中: {title}")

    response = requests.post(
        f"{API_BASE}/posts",
        json=post_data,
        auth=AUTH,
        timeout=30,
    )

    if response.status_code != 201:
        raise Exception(
            f"投稿作成失敗: HTTP {response.status_code}\n"
            f"レスポンス: {response.text[:500]}"
        )

    post = response.json()

    print(f"[OK] 下書き投稿作成成功!")
    print(f"  - Post ID: {post['id']}")
    print(f"  - ステータス: {post['status']}")
    print(f"  - 編集URL: {WP_URL}/wp-admin/post.php?post={post['id']}&action=edit")
    print(f"  - プレビューURL: {post.get('link', 'N/A')}?preview=true")

    return post


# ============================================================
# メインワークフロー
# ============================================================

def main():
    """
    完全なワークフロー:
    1. API接続・認証確認
    2. アイキャッチ画像をアップロード
    3. 記事本文用の画像をアップロード
    4. Gutenbergブロック形式で記事本文を組み立て
    5. 下書き投稿を作成（アイキャッチ + 本文中画像 + Yoast SEO設定）
    """

    print("=" * 60)
    print("WordPress REST API 自動投稿ワークフロー")
    print("=" * 60)

    # ----------------------------------------------------------
    # Step 0: 接続・認証確認
    # ----------------------------------------------------------
    print("\n--- Step 0: 接続・認証確認 ---")
    if not check_connection():
        return
    if not check_authentication():
        return

    # ----------------------------------------------------------
    # Step 1: アイキャッチ画像のアップロード
    # ----------------------------------------------------------
    print("\n--- Step 1: アイキャッチ画像のアップロード ---")

    eyecatch_image_path = "/path/to/eyecatch-image.jpg"  # ★ 実際のパスに変更

    eyecatch_media = upload_image(
        file_path=eyecatch_image_path,
        title="記事のアイキャッチ画像",
        alt_text="記事のメインビジュアル - 説明テキスト",
        caption="",
    )
    eyecatch_media_id = eyecatch_media["id"]

    # ----------------------------------------------------------
    # Step 2: 本文中に埋め込む画像のアップロード
    # ----------------------------------------------------------
    print("\n--- Step 2: 本文用画像のアップロード ---")

    content_image_path = "/path/to/content-image.png"  # ★ 実際のパスに変更

    content_media = upload_image(
        file_path=content_image_path,
        title="記事内の解説画像",
        alt_text="手順を説明するスクリーンショット",
        caption="図1: 設定手順のスクリーンショット",
    )
    content_image_url = content_media["source_url"]
    content_image_id = content_media["id"]

    # ----------------------------------------------------------
    # Step 3: 記事本文の組み立て（Gutenbergブロック形式）
    # ----------------------------------------------------------
    print("\n--- Step 3: 記事本文の組み立て ---")

    blocks = [
        block_paragraph(
            "この記事では、WordPress REST APIを使った自動投稿の方法を解説します。"
            "Pythonスクリプトから画像のアップロードと記事の投稿を行います。"
        ),

        block_heading("準備するもの", level=2),

        block_list([
            "Python 3.8以上",
            "requestsライブラリ",
            "WordPressのアプリケーションパスワード",
        ]),

        block_heading("実装手順", level=2),

        block_paragraph(
            "以下のスクリーンショットのように設定を行います。"
        ),

        # 本文中に画像を埋め込み
        block_image(
            image_url=content_image_url,
            image_id=content_image_id,
            alt_text="手順を説明するスクリーンショット",
            caption="図1: 設定手順のスクリーンショット",
            size_slug="large",
        ),

        block_paragraph(
            "上記の手順に従って設定すれば、自動投稿が可能になります。"
        ),

        block_heading("まとめ", level=2),

        block_paragraph(
            "WordPress REST APIを使えば、Pythonから効率的に記事を管理できます。"
            "アプリケーションパスワードを使用することで、安全にAPIへアクセスできます。"
        ),
    ]

    content = build_content(blocks)
    print(f"[OK] 記事本文を組み立てました（{len(content):,} 文字）")

    # ----------------------------------------------------------
    # Step 4: 下書き投稿の作成
    # ----------------------------------------------------------
    print("\n--- Step 4: 下書き投稿の作成 ---")

    post = create_draft_post(
        title="【Python】WordPress REST APIで画像付き記事を自動投稿する方法",
        content=content,
        featured_media_id=eyecatch_media_id,
        # categories=[1],  # ★ 実際のカテゴリIDに変更
        # tags=[10, 20],    # ★ 実際のタグIDに変更
        excerpt="PythonとWordPress REST APIを使って、画像付きの記事を自動投稿する方法を解説します。",
        slug="wordpress-rest-api-python-auto-post",
        # Yoast SEO メタデータ
        yoast_title="WordPress REST APIでPython自動投稿 %%sep%% %%sitename%%",
        yoast_metadesc="PythonのrequestsライブラリとWordPress REST APIを使って、画像アップロードから記事投稿までを自動化する方法を詳しく解説します。",
        yoast_focuskw="WordPress REST API Python",
        yoast_og_title="【Python】WordPress REST APIで画像付き記事を自動投稿",
        yoast_og_description="PythonでWordPressの記事投稿を自動化！REST APIの使い方を解説。",
    )

    # ----------------------------------------------------------
    # 完了
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("ワークフロー完了!")
    print(f"  投稿ID: {post['id']}")
    print(f"  編集URL: {WP_URL}/wp-admin/post.php?post={post['id']}&action=edit")
    print("  ステータス: 下書き（管理画面で確認・公開してください）")
    print("=" * 60)

    return post


# ============================================================
# エントリーポイント
# ============================================================

if __name__ == "__main__":
    main()
```

### 6.4 複数画像を一括アップロードするヘルパー

```python
def upload_multiple_images(image_configs):
    """
    複数の画像を一括アップロードする

    Args:
        image_configs (list[dict]): 画像設定のリスト
            各dictは {file_path, title, alt_text, caption} を持つ

    Returns:
        list[dict]: アップロードされたメディア情報のリスト
    """
    results = []

    for i, config in enumerate(image_configs, 1):
        print(f"\n[{i}/{len(image_configs)}] アップロード中...")
        try:
            media = upload_image(
                file_path=config["file_path"],
                title=config.get("title"),
                alt_text=config.get("alt_text"),
                caption=config.get("caption"),
            )
            results.append(media)
        except Exception as e:
            print(f"[ERROR] {config['file_path']}: {e}")
            results.append(None)

    successful = sum(1 for r in results if r is not None)
    print(f"\n[SUMMARY] {successful}/{len(image_configs)} 件のアップロードが成功")

    return results


# 使用例
images = [
    {
        "file_path": "/path/to/image1.jpg",
        "title": "画像1",
        "alt_text": "画像1の説明",
        "caption": "キャプション1",
    },
    {
        "file_path": "/path/to/image2.png",
        "title": "画像2",
        "alt_text": "画像2の説明",
        "caption": "キャプション2",
    },
]

media_list = upload_multiple_images(images)
```

---

## 7. トラブルシューティング

### 7.1 よくあるエラーと対処法

| エラー | 原因 | 対処法 |
|--------|------|--------|
| `401 Unauthorized` | 認証失敗 | ユーザー名・アプリケーションパスワードを確認。HTTPS必須。 |
| `403 Forbidden` | 権限不足 | ユーザーに適切な権限（編集者以上）があるか確認 |
| `rest_cannot_create` | REST API無効 | パーマリンク設定が「基本」以外になっているか確認 |
| `rest_upload_no_content_disposition` | ヘッダー不足 | `Content-Disposition` ヘッダーを追加 |
| `rest_upload_file_too_big` | ファイルサイズ超過 | サーバーの `upload_max_filesize` を確認 |
| `rest_no_route` | エンドポイント不存在 | URLが正しいか確認。パーマリンク設定を再保存 |
| `413 Request Entity Too Large` | Nginx/Apacheの制限 | Webサーバーの `client_max_body_size`（Nginx）を確認 |
| 画像がアップロードされるがメタデータが設定されない | メタデータ更新の問題 | アップロード後に別途PUTリクエストでメタデータを更新 |
| Yoast SEOのフィールドが保存されない | `show_in_rest` 未登録 | `functions.php` でメタキーを `register_meta()` する |

### 7.2 REST APIが有効か確認する方法

```python
# REST APIのディスカバリーエンドポイント
response = requests.get(f"{WP_URL}/wp-json/")
if response.status_code == 200:
    data = response.json()
    print(f"サイト名: {data['name']}")
    print(f"REST API URL: {data['url']}")
    print(f"利用可能な名前空間: {data['namespaces']}")
else:
    print("REST APIが無効です")
```

### 7.3 パーマリンク設定の確認

REST APIが動作するためには、WordPressのパーマリンク設定が「基本」以外に設定されている必要がある:

1. 管理画面 → **設定** → **パーマリンク** に移動
2. **「基本」以外**の設定（例: 「投稿名」）を選択
3. **「変更を保存」** をクリック

### 7.4 デバッグ用コード

```python
def debug_request(method, url, **kwargs):
    """デバッグ用のリクエストラッパー"""
    print(f"\n[DEBUG] {method} {url}")
    if "json" in kwargs:
        print(f"  Body: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)[:500]}")
    if "headers" in kwargs:
        safe_headers = {k: v for k, v in kwargs["headers"].items()
                       if k.lower() != "authorization"}
        print(f"  Headers: {safe_headers}")

    response = requests.request(method, url, **kwargs)

    print(f"  Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"  Error: {response.text[:300]}")

    return response
```

### 7.5 マルチパートフォームデータでのアップロード（代替方法）

バイナリ送信でうまくいかない場合、マルチパートフォームデータ形式も使用可能:

```python
def upload_image_multipart(file_path, title=None, alt_text=None):
    """マルチパートフォームデータ方式での画像アップロード"""
    file_name = os.path.basename(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    with open(file_path, "rb") as f:
        files = {
            "file": (file_name, f, mime_type),
        }
        data = {}
        if title:
            data["title"] = title
        if alt_text:
            data["alt_text"] = alt_text

        response = requests.post(
            f"{API_BASE}/media",
            files=files,
            data=data,
            auth=AUTH,
            timeout=60,
        )

    if response.status_code != 201:
        raise Exception(f"アップロード失敗: {response.status_code} - {response.text}")

    return response.json()
```

> **注意:** マルチパートフォームデータ方式では、`requests` ライブラリが `Content-Type` と `Content-Disposition` を自動設定するため、手動でヘッダーを設定する必要がない。ただし、一部のWordPress環境ではバイナリ方式のほうが安定する場合がある。

---

## 付録

### A. 参考リンク

| リソース | URL |
|---------|-----|
| WordPress REST API 公式リファレンス | https://developer.wordpress.org/rest-api/reference/ |
| Posts エンドポイント | https://developer.wordpress.org/rest-api/reference/posts/ |
| Media エンドポイント | https://developer.wordpress.org/rest-api/reference/media/ |
| 認証ガイド | https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/ |
| アプリケーションパスワード | https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/ |
| Yoast SEO REST API | https://developer.yoast.com/features/rest-api/ |
| Cocoonテーマ公式 | https://wp-cocoon.com/ |

### B. HTTPステータスコード一覧（REST API関連）

| コード | 意味 | 説明 |
|--------|------|------|
| 200 | OK | 取得・更新成功 |
| 201 | Created | 新規作成成功（投稿・メディア作成時） |
| 400 | Bad Request | リクエストパラメータ不正 |
| 401 | Unauthorized | 認証失敗 |
| 403 | Forbidden | 権限不足 |
| 404 | Not Found | エンドポイント・リソースが存在しない |
| 413 | Payload Too Large | アップロードサイズ超過 |
| 500 | Internal Server Error | サーバーエラー |

### C. 実行前チェックリスト

- [ ] WordPress 5.6以上であること
- [ ] HTTPS が有効であること
- [ ] パーマリンク設定が「基本」以外であること
- [ ] アプリケーションパスワードが発行済みであること
- [ ] APIユーザーに「編集者」以上の権限があること
- [ ] `.env` ファイルに認証情報を設定済みであること
- [ ] `pip install requests python-dotenv` を実行済みであること
- [ ] Yoast SEO プラグインが有効であること（SEOメタデータを設定する場合）
- [ ] 画像ファイルのパスが正しいこと
