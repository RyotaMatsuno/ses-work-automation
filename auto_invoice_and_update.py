"""
auto_invoice_and_update.py v2 (Googleスプレッドシート対応版)
=============================================================
freee請求書作成 → Googleスプレッドシートステータス自動更新

使い方:
  python auto_invoice_and_update.py           # 翌月分（デフォルト）
  python auto_invoice_and_update.py 2026-06   # 月指定
  python auto_invoice_and_update.py --dry-run # ドライラン
"""

import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee")

from datetime import date

from sheets_reader import scan_nyujomae, update_to_kado


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if not a.startswith("-")]

    target_month = None
    if args:
        try:
            y, m = map(int, args[0].split("-"))
            target_month = date(y, m, 1)
        except Exception:
            print(f"[WARN] 月指定パース失敗: {args[0]} → デフォルト（翌月）で実行")

    print("=" * 55)
    print("  freee請求書作成 + Sheetsステータス自動更新")
    if dry_run:
        print("  ※ドライランモード: Sheets更新・freeeスキップ")
    print("=" * 55)

    # --- Step1: 入場前スキャン ---
    print("\n[SCAN] Googleスプレッドシートをスキャン中...")
    nyujomae = scan_nyujomae()
    if nyujomae:
        print(f"[SCAN] 入場前: {len(nyujomae)}名")
        for t in nyujomae:
            print(f"       {t['sheet']} | {t['name']}")
    else:
        print("[SCAN] 入場前: 0名")

    # --- Step2: freee請求書作成 ---
    if not dry_run:
        print("\n[freee] 請求書ドラフト作成...")
        from freee_invoice_v2_sheets import run as freee_run

        freee_run(target_month)
    else:
        print("\n[DRY-RUN] freeeスキップ")

    # --- Step3: Sheetsステータス更新 ---
    if nyujomae and not dry_run:
        print("\n[Sheets] ステータス更新中...")
        updated = update_to_kado(nyujomae, execute=True)
        if updated:
            print(f"[OK] {len(updated)}名を稼働中に更新:")
            for u in updated:
                print(f"     {u}")
        else:
            print("[INFO] 更新対象なし")
    elif dry_run:
        print("\n[DRY-RUN] Sheets更新スキップ")

    print("\n" + "=" * 55)
    print("  完了")
    print("=" * 55)


if __name__ == "__main__":
    main()
