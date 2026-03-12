"""
Gemini API 使用量トラッカー

実際の請求額は https://aistudio.google.com/spend で確認できる（円建て）。
このスクリプトは:
  - 画像生成ごとの概算コストをローカルに記録（枚数ベース）
  - 実際のGoogle請求額（円）を手動記録できる
  - 月次予算超過の場合に API 生成スキップを指示する

使用方法:
    python lib/usage_tracker.py                    # 今月の状況を表示
    python lib/usage_tracker.py --record 147       # 実績額を手動記録（円）
    python lib/usage_tracker.py --reset            # 今月の推定記録をリセット
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────
# 概算コスト定数（円）
# USD価格 × 150円/USD の近似値
# 実際の請求は https://aistudio.google.com/spend で確認すること
# ──────────────────────────────────────────────
COST_TABLE_JPY = {
    ("eyecatch",      "1K"): 10,
    ("eyecatch",      "2K"): 15,
    ("eyecatch",      "4K"): 23,
    ("illustration",  None): 10,
    ("illustration",  "1K"): 10,
    ("illustration",  "2K"): 15,
}

MONTHLY_BUDGET_JPY: int = 1500   # 円（≈ $10）
WARNING_THRESHOLD:  float = 0.80  # 80% で警告
SKIP_THRESHOLD:     float = 1.00  # 100% で生成スキップ

SPEND_URL = "https://aistudio.google.com/spend"

_LOG_PATH = Path.home() / ".claude" / "projects" / "gemini_usage.json"


# ──────────────────────────────────────────────
# UsageTracker クラス
# ──────────────────────────────────────────────

class UsageTracker:
    """Gemini API の画像生成コストをローカルファイルで管理するクラス。"""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or _LOG_PATH
        self._ensure_log_file()

    def _ensure_log_file(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text(
                json.dumps({"records": [], "actual_costs": {}}, indent=2)
            )

    def _load(self) -> dict:
        data = json.loads(self.log_path.read_text(encoding="utf-8"))
        data.setdefault("actual_costs", {})
        return data

    def _save(self, data: dict) -> None:
        self.log_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _month_key(self, year: int, month: int) -> str:
        return f"{year}-{month:02d}"

    # ── 記録 ──────────────────────────────────

    def record(self, image_type: str, model: str, size: Optional[str] = None) -> int:
        """画像1枚の生成を記録し、概算コスト（円）を返す。"""
        cost = COST_TABLE_JPY.get((image_type, size)) \
            or COST_TABLE_JPY.get((image_type, None), 10)

        data = self._load()
        data["records"].append({
            "date":       datetime.now().isoformat(),
            "image_type": image_type,
            "model":      model,
            "size":       size,
            "cost_jpy":   cost,
        })
        self._save(data)
        return cost

    def record_actual(self, amount_jpy: int, year: int = None, month: int = None) -> None:
        """Google の請求画面で確認した実績額（円）を記録する。"""
        now = datetime.now()
        key = self._month_key(year or now.year, month or now.month)

        data = self._load()
        data["actual_costs"][key] = {
            "amount_jpy":   amount_jpy,
            "recorded_at":  datetime.now().isoformat(),
        }
        self._save(data)

    # ── 集計 ──────────────────────────────────

    def get_monthly_stats(self, year: int = None, month: int = None) -> dict:
        """指定月の使用量統計を返す。

        Returns:
            estimated_jpy   画像枚数ベースの概算コスト（円）
            actual_jpy      手動記録した実績額（None = 未記録）
            display_jpy     表示用コスト（実績優先、なければ概算）
            total_images    生成枚数
            projected_jpy   月末予測（概算ベース）
            budget_jpy      月次予算
            budget_used_pct 予算消費率 (%)
        """
        now   = datetime.now()
        year  = year  or now.year
        month = month or now.month
        key   = self._month_key(year, month)

        data = self._load()

        monthly = [
            r for r in data["records"]
            if datetime.fromisoformat(r["date"]).year  == year
            and datetime.fromisoformat(r["date"]).month == month
        ]

        estimated = sum(r.get("cost_jpy", 10) for r in monthly)
        total_images = len(monthly)

        elapsed_days  = max(now.day, 1)
        projected = int((estimated / elapsed_days) * 30) if elapsed_days > 0 else 0

        actual_entry = data["actual_costs"].get(key)
        actual_jpy   = actual_entry["amount_jpy"] if actual_entry else None
        display_jpy  = actual_jpy if actual_jpy is not None else estimated

        return {
            "year":          year,
            "month":         month,
            "estimated_jpy": estimated,
            "actual_jpy":    actual_jpy,
            "display_jpy":   display_jpy,
            "total_images":  total_images,
            "projected_jpy": projected,
            "budget_jpy":    MONTHLY_BUDGET_JPY,
            "budget_used_pct": round(display_jpy / MONTHLY_BUDGET_JPY * 100, 1),
        }

    def check_budget(self) -> dict:
        """現在の予算状況を返す。生成可否の判定フラグを含む。"""
        stats = self.get_monthly_stats()
        amt   = stats["display_jpy"]
        stats["should_warn"] = amt >= MONTHLY_BUDGET_JPY * WARNING_THRESHOLD
        stats["should_skip"] = amt >= MONTHLY_BUDGET_JPY * SKIP_THRESHOLD
        stats["spend_url"]   = SPEND_URL
        return stats

    def reset_month(self, year: int = None, month: int = None) -> int:
        """指定月の推定記録（画像ログ）を削除する。実績額は保持。"""
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
# CLI
# ──────────────────────────────────────────────

def _print_stats(stats: dict) -> None:
    year, month = stats["year"], stats["month"]
    print("=" * 52)
    print(f"  Gemini API 使用量  {year}/{month:02d}")
    print("=" * 52)
    print(f"  生成枚数        : {stats['total_images']} 枚")
    if stats["actual_jpy"] is not None:
        print(f"  実績額（確認済）: ¥{stats['actual_jpy']:,}")
        print(f"  概算額          : ¥{stats['estimated_jpy']:,}（参考）")
    else:
        print(f"  概算コスト      : ¥{stats['estimated_jpy']:,}")
        print(f"  月末予測        : ¥{stats['projected_jpy']:,}（概算）")
        print(f"  ※ 実績は {SPEND_URL} で確認できます")
    print(f"  月次予算        : ¥{stats['budget_jpy']:,}")
    print(f"  予算消費率      : {stats['budget_used_pct']:.1f}%")

    if stats.get("should_skip"):
        print(f"\n  ⚠️  予算超過: API 生成をスキップしてプロンプト出力のみに切り替えます")
    elif stats.get("should_warn"):
        print(f"\n  ⚠️  警告: 予算の {int(WARNING_THRESHOLD*100)}% を超えています")
    print("=" * 52)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini API 使用量トラッカー")
    parser.add_argument(
        "--record", type=int, metavar="AMOUNT_JPY",
        help="Google の請求画面で確認した今月の実績額（円）を記録する",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="今月の推定記録（画像ログ）をリセットする（実績額は保持）",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="結果を JSON 形式で出力する（スクリプト連携用）",
    )
    args = parser.parse_args()

    tracker = UsageTracker()

    if args.record is not None:
        tracker.record_actual(args.record)
        print(f"今月の実績額を ¥{args.record:,} として記録しました。")
        print(f"（確認元: {SPEND_URL}）")
        return

    if args.reset:
        deleted = tracker.reset_month()
        print(f"今月の推定記録を {deleted} 件削除しました。（実績額は保持）")
        return

    stats = tracker.check_budget()

    if args.json:
        print(json.dumps(stats, ensure_ascii=False))
        return

    _print_stats(stats)

    if stats["should_skip"]:
        sys.exit(2)
    if stats["should_warn"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
