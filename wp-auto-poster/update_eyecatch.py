"""
投稿ID 1010 のアイキャッチ画像を新しい画像で置き換える
"""
import sys
from pathlib import Path

from lib.wp_client import WordPressClient

# 設定
eyecatch_path = "/Users/totsu00/ClaudeCodeWork/drafts/2026-03-13_claude-in-chrome-skill/images/eyecatch.png"
alt_text = "Claude in Chromeスキルの仕組みを示すフロー図：ClaudeコードとChromeブラウザをSKILL.mdが繋ぐ概念図"
post_id = 1010

print("=" * 60)
print("アイキャッチ画像の差し替え")
print("=" * 60)

# ファイル存在確認
if not Path(eyecatch_path).exists():
    print(f"[エラー] ファイルが見つかりません: {eyecatch_path}")
    sys.exit(1)

# WordPressクライアント初期化
client = WordPressClient()

# 画像アップロード
print(f"\n1. 画像をメディアライブラリにアップロード中...")
try:
    media_result = client.upload_media(
        file_path=eyecatch_path,
        alt_text=alt_text,
        title="Claude in Chromeスキル"
    )
    media_id = media_result["id"]
    print(f"[OK] アップロード完了: media_id={media_id}")
    print(f"     URL: {media_result['url']}")
except Exception as e:
    print(f"[NG] アップロード失敗: {e}")
    sys.exit(1)

# 投稿のアイキャッチを更新
print(f"\n2. 投稿ID {post_id} のアイキャッチを更新中...")
try:
    # update_post呼び出し時に featured_media_id のみを更新
    # 本文は変更しないために、実際には変更を反映させない工夫が必要
    # wp_client.py の update_post は content を必須にしているため、
    # 実際には POST /posts/{id} に featured_media_id のみを送信する必要がある
    
    # 直接 _request を使ってAPIを呼び出し
    import json as json_module
    resp = client._request(
        "POST",
        f"/posts/{post_id}",
        json={"featured_media": media_id}
    )
    post = resp.json()
    
    edit_url = f"{client.site_url}/wp-admin/post.php?post={post_id}&action=edit"
    print(f"[OK] 更新完了")
    print(f"     編集URL: {edit_url}")
except Exception as e:
    print(f"[NG] 更新失敗: {e}")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"アイキャッチ画像の差し替え完了！")
print(f"  メディアID: {media_id}")
print(f"  投稿ID: {post_id}")
print(f"  編集URL: {edit_url}")
print(f"{'='*60}")
