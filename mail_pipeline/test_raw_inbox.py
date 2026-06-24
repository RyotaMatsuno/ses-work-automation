"""raw_inbox.py のユニットテスト"""

import json
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

from mail_pipeline.raw_inbox import (
    count_processed,
    count_rows,
    init_db,
    insert_raw_email,
    load_processed_ids,
    mark_processed,
    migrate_processed_ids_json,
    monthly_stats_rows,
    update_classify_result,
)


def run_tests():
    passed = 0
    failed = 0

    def ok(name):
        nonlocal passed
        passed += 1
        print(f"  [OK] {name}")

    def ng(name, reason):
        nonlocal failed
        failed += 1
        print(f"  [NG] {name}: {reason}")

    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "test.db"

        # 1. init_db: DBを作成できる
        try:
            init_db(db)
            assert db.exists()
            ok("init_db: DB作成")
        except Exception as e:
            ng("init_db: DB作成", str(e))

        # 2. insert_raw_email: 新規レコード挿入
        try:
            result = insert_raw_email(
                message_id="<test-001@example.com>",
                account="sessales",
                received_at="2026-06-18T10:00:00",
                sender="test@example.com",
                subject="【案件】Java開発テスト",
                body_text="テスト本文",
                has_attachment=False,
                db_path=db,
            )
            assert result is True
            assert count_rows(db) == 1
            ok("insert_raw_email: 新規挿入")
        except Exception as e:
            ng("insert_raw_email: 新規挿入", str(e))

        # 3. insert_raw_email: 重複挿入はFalseを返す（UNIQUE制約）
        try:
            result = insert_raw_email(
                message_id="<test-001@example.com>",
                account="sessales",
                received_at="2026-06-18T10:00:00",
                sender="test@example.com",
                subject="【案件】Java開発テスト",
                body_text="テスト本文",
                db_path=db,
            )
            assert result is False
            assert count_rows(db) == 1
            ok("insert_raw_email: 重複挿入はFalse")
        except Exception as e:
            ng("insert_raw_email: 重複挿入はFalse", str(e))

        # 4. mark_processed: 処理済みフラグ更新
        try:
            mark_processed("<test-001@example.com>", classify_result="project", db_path=db)
            assert count_processed(db) == 1
            ok("mark_processed: フラグ更新")
        except Exception as e:
            ng("mark_processed: フラグ更新", str(e))

        # 5. load_processed_ids: 処理済みIDセット読み込み
        try:
            ids = load_processed_ids(db)
            assert "<test-001@example.com>" in ids
            ok("load_processed_ids: セット読み込み")
        except Exception as e:
            ng("load_processed_ids: セット読み込み", str(e))

        # 6. update_classify_result: 分類結果更新
        try:
            update_classify_result("<test-001@example.com>", "skip", db_path=db)
            ok("update_classify_result: 分類結果更新")
        except Exception as e:
            ng("update_classify_result: 分類結果更新", str(e))

        # 7. monthly_stats ビュー
        try:
            rows = monthly_stats_rows(db)
            assert isinstance(rows, list)
            ok("monthly_stats: ビュー参照")
        except Exception as e:
            ng("monthly_stats: ビュー参照", str(e))

        # 8. migrate_processed_ids_json: JSON→SQLite移行
        try:
            db2 = Path(tmpdir) / "test2.db"
            json_path = Path(tmpdir) / "processed_ids.json"
            bak_path = Path(tmpdir) / "processed_ids.json.bak"
            test_ids = ["<msg-001@test>", "<msg-002@test>", "<msg-003@test>"]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(test_ids, f)
            migrated = migrate_processed_ids_json(json_path, db2, bak_path)
            assert migrated == 3
            assert not json_path.exists()
            assert bak_path.exists()
            assert count_processed(db2) == 3
            ok("migrate_processed_ids_json: JSON移行")
        except Exception as e:
            ng("migrate_processed_ids_json: JSON移行", str(e))

        # 9. mark_processed: 存在しないIDも挿入できる
        try:
            mark_processed("<new-msg@test>", classify_result="project", db_path=db)
            ids = load_processed_ids(db)
            assert "<new-msg@test>" in ids
            ok("mark_processed: 新規IDも挿入")
        except Exception as e:
            ng("mark_processed: 新規IDも挿入", str(e))

    print(f"\n結果: {passed}件成功 / {failed}件失敗")
    return failed == 0


if __name__ == "__main__":
    print("=== raw_inbox.py テスト ===")
    success = run_tests()
    sys.exit(0 if success else 1)
