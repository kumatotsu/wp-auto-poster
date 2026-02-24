"""
環境変数の読み込みと設定管理

.env ファイルから認証情報・設定を読み込み、アプリケーション全体で使用する。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートの.envを読み込み
_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)

# ──────────────────────────────────────────────
# WordPress設定
# ──────────────────────────────────────────────
WP_URL: str = os.getenv("WP_URL", "https://m-totsu.com").rstrip("/")
WP_USER: str = os.getenv("WP_USER", "")
WP_APP_PASSWORD: str = os.getenv("WP_APP_PASSWORD", "")

WP_REST_BASE: str = f"{WP_URL}/wp-json/wp/v2"

# ──────────────────────────────────────────────
# Google Gemini API設定
# ──────────────────────────────────────────────
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

# 画像生成モデル設定
EYECATCH_MODEL: str = "gemini-3-pro-image-preview"
EYECATCH_SIZE: str = "2K"
EYECATCH_ASPECT: str = "16:9"

ILLUSTRATION_MODEL: str = "gemini-2.5-flash-image"
ILLUSTRATION_ASPECT: str = "4:3"

# ──────────────────────────────────────────────
# もしもアフィリエイト設定
# ──────────────────────────────────────────────
MOSHIMO_AMAZON_AID: str = os.getenv("MOSHIMO_AMAZON_AID", "")
MOSHIMO_RAKUTEN_AID: str = os.getenv("MOSHIMO_RAKUTEN_AID", "")
MOSHIMO_AMAZON_PLID: str = os.getenv("MOSHIMO_AMAZON_PLID", "27060")
MOSHIMO_RAKUTEN_PLID: str = os.getenv("MOSHIMO_RAKUTEN_PLID", "27059")

# プラットフォーム固定値（もしもアフィリエイト共通）
MOSHIMO_AMAZON_PID: str = "170"
MOSHIMO_AMAZON_PCID: str = "185"
MOSHIMO_RAKUTEN_PID: str = "54"
MOSHIMO_RAKUTEN_PCID: str = "54"

# かんたんリンクスクリプトURL
MOSHIMO_SCRIPT_URL: str = "//dn.msmstatic.com/site/cardlink/bundle.js?20210203"

# ──────────────────────────────────────────────
# パス設定
# ──────────────────────────────────────────────
PROJECT_ROOT: Path = _project_root.parent  # ClaudeCodeWork/
DRAFTS_DIR: Path = PROJECT_ROOT / "drafts"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
PROMPTS_DIR: Path = _project_root / "prompts"
MERMAID_CONFIG: Path = _project_root / "mermaid-config.json"

# ──────────────────────────────────────────────
# バリデーション
# ──────────────────────────────────────────────

def validate_wp_config() -> list[str]:
    """WordPress設定のバリデーション。不足項目をリストで返す。"""
    errors = []
    if not WP_USER:
        errors.append("WP_USER が設定されていません")
    if not WP_APP_PASSWORD:
        errors.append("WP_APP_PASSWORD が設定されていません")
    if not WP_URL.startswith("https://"):
        errors.append(f"WP_URL がHTTPSではありません: {WP_URL}")
    return errors


def validate_gemini_config() -> list[str]:
    """Gemini API設定のバリデーション。不足項目をリストで返す。"""
    errors = []
    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY が設定されていません")
    return errors


def validate_moshimo_config() -> list[str]:
    """もしもアフィリエイト設定のバリデーション。不足項目をリストで返す。"""
    errors = []
    if not MOSHIMO_AMAZON_AID:
        errors.append("MOSHIMO_AMAZON_AID が設定されていません")
    if not MOSHIMO_RAKUTEN_AID:
        errors.append("MOSHIMO_RAKUTEN_AID が設定されていません")
    return errors
