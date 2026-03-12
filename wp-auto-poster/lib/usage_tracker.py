"""
Gemini API 使用量トラッカー

画像生成ごとにコストをローカルファイルで記録・集計する。
月次コストが予算に近づいた場合に警告し、超過時はプロンプト出力のみに切り替える判定を行う。

使用方法:
    python lib/usage_tracker.py           # 今月の使用量を表示
    python lib/usage_tracker.py --reset   # 今月の記録をリセット
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────
# コスト定数 (USD, 2026年3月時点)
# ──────────────────────────────────────────────
COST_TABLE = {
    ("eyecatch", "1K"):        0.067,
    ("eyecatch", "2K"):        0.101,
    ("eyecatch", "4K"):        0.151,
    ("illustration", None):    0.067,  # サイズ未指定 → 1K相当
    ("illustration", "1K"):    0.067,
    ("illustration", "2K"):    0.101,
}

# 月次予算
MONTHLY_BUDGET_USD: float = 10.0

# 警告閾値（予算の何%で警告するか）
WARNING_THRESHOLD: float = 0.80   # 80%
SKIP_THRESHOLD: float    = 1.00   # 100%（超過したら生成スキップ）

# 使用量ログの保存先（ユーザーホームの .claude/ 以下で永続管理）
_LOG_PATH = Path.home() / ".claude" / "projects" / "gemini_usage.json"


# ──────────────────────────────────────────────
# UsageTracker クラス
# ──────────────────────────────────────────────

class UsageTracker:
    """Gemini API の画像生成コストをローカルファイルで管理するクラス。"""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or _LOG_PATH
        self._ensure_log_file()

    # ── 内部ユーティリティ ──────────────────────

    def _ensure_log_file(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text(json.dumps({"records": []}, indent=2))

    def _load(self) -> dict:
        return json.loads(self.log_path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.log_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── 公開メソッド ────────────────────────────

    def record(self, image_type: str, model: str, size: Optional[str] = None) -> float:
        """画像1枚の生成コストを記録し、コスト (USD) を返す。

        Args:
            image_type: "eyecatch" または "illustration"
            model: 使用モデル名（ログ用）
            size: 画像サイズ文字列（"1K", "2K" など）

        Returns:
            記録したコスト (USD)
        """
        cost = COST_TABLE.get((image_type, size)) or COST_TABLE.get((image_type, None), 0.067)

        data = self._load()
        data["records"].append({
            "date":       datetime.now().isoformat(),
            "image_type": image_type,
            "model":      model,
            "size":       size,
            "cost_usd":   cost,
        })
        self._save(data)
        return cost

    def get_monthly_stats(self, year: int = None, month: int = None) -> dict:
        """指定月の使用量統計を返す。

        Returns:
            dict:
                total_cost_usd          今月累計コスト
                total_images            生成枚数
                projected_monthly_usd   月末まで同ペースの場合の予測コスト
                budget_usd              月次予算
                budget_used_pct         予算消費率 (%)
                records                 レコード一覧
        """
        now = datetime.now()
        year  = year  or now.year
        month = month or now.month

        data = self._load()
        monthly = [
            r for r in data["records"]
            if (
                datetime.fromisoformat(r["date"]).year  == year and
                datetime.fromisoformat(r["date"]).month == month
            )
        ]

        total_cost   = sum(r["cost_usd"] for r in monthly)
        total_images = len(monthly)

        # 月末予測: 経過日数ベースで線形外挿（月初は当日ぶんのみで計算）
        elapsed_days = max(now.day, 1)
        days_in_month = 30  # 簡略近似
        projected = (total_cost / elapsed_days) * days_in_month if elapsed_days > 0 else 0.0

        return {
            "year":                    year,
            "month":                   month,
            "total_cost_usd":          round(total_cost,   4),
            "total_images":            total_images,
            "projected_monthly_usd":   round(projected,    4),
            "budget_usd":              MONTHLY_BUDGET_USD,
            "budget_used_pct":         round(total_cost / MONTHLY_BUDGET_USD * 100, 1),
            "records":                 monthly,
        }

    def check_budget(self) -> dict:
        """現在の予算状況を返す。生成可否の判定フラグを含む。

        Returns:
            dict:
                ...get_monthly_stats() の全フィールド...
                should_warn: True なら警告を表示すべき
                should_skip: True なら API 生成をスキップしてプロンプト出力のみにすべき
        """
        stats = self.get_monthly_stats()
        used  = stats["total_cost_usd"]
        stats["should_warn"] = used >= MONTHLY_BUDGET_USD * WARNING_THRESHOLD
        stats["should_skip"] = used >= MONTHLY_BUDGET_USD * SKIP_THRESHOLD
        return stats

    def reset_month(self, year: int = None, month: int = None) -> int:
        """指定月のレコードを削除し、削除件数を返す。"""
        now   = datetime.now()
        year  = year  or now.year
        month = month or now.month

        data = self._load()
        before = len(data["records"])
        data["records"] = [
            r for r in data["records"]
            if not (
                datetime.fromisoformat(r["date"]).year  == year and
                datetime.fromisoformat(r["date"]).month == month
            )
        ]
        deleted = before - len(data["records"])
        self._save(data)
        return deleted


# ──────────────────────────────────────────────
# CLI インターフェース
# ──────────────────────────────────────────────

def _print_stats(stats: dict) -> None:
    """統計情報を人間が読みやすい形式で標準出力に出力する。"""
    print("=" * 50)
    print(f"  Gemini API 使用量 ({stats['year']}/{stats['month']:02d})")
    print("=" * 50)
    print(f"  生成枚数       : {stats['total_images']} 枚")
    print(f"  今月累計コスト : ${stats['total_cost_usd']:.4f}")
    print(f"  月末予測コスト : ${stats['projected_monthly_usd']:.4f}")
    print(f"  月次予算       : ${stats['budget_usd']:.2f}")
    print(f"  予算消費率     : {stats['budget_used_pct']:.1f}%")

    if stats.get("should_skip"):
        print("\n  ⚠️  予算超過: 画像生成をスキップしてプロンプト出力のみに切り替えます")
    elif stats.get("should_warn"):
        print(f"\n  ⚠️  警告: 予算の {WARNING_THRESHOLD*100:.0f}% を超えています")

    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gemini API 使用量トラッカー",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="今月の記録をリセットする",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="結果を JSON 形式で出力する（スクリプト連携用）",
    )
    args = parser.parse_args()

    tracker = UsageTracker()

    if args.reset:
        deleted = tracker.reset_month()
        print(f"今月のレコードを {deleted} 件削除しました。")
        return

    stats = tracker.check_budget()

    if args.json:
        # スクリプトから呼び出す場合は JSON を標準出力に出力
        print(json.dumps(stats, ensure_ascii=False))
        return

    _print_stats(stats)

    # 終了コード: should_skip なら 2、should_warn なら 1、正常なら 0
    if stats["should_skip"]:
        sys.exit(2)
    if stats["should_warn"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
