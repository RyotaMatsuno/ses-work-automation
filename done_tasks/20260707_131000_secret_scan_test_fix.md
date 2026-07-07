# secret_scanテストの自己検知修正（小・2026-07-07）

事象: pre-pushフックが tests/test_secret_scan.py 自身のダミーキー（検知テスト用の
リテラル文字列）を検知してpushをブロック（13:0x実測。フック本体は正常動作）。

## 修正
- tests/test_secret_scan.py 内の全ダミーシークレットを実行時連結で構築する方式に変更
  例: FAKE_GCP = "AI" + "za" + "x" * 35 / FAKE_PK = "-----BEGIN " + "PRIVATE KEY-----"
  ソース上にパターン完全一致のリテラルを残さないこと
- スキャナ本体へのallowlist追加はしない（穴になるため）
- 修正後、フックを通してpushが成功することを確認: git push origin main
  （現在ローカル1コミットがpush待ち）

## 完了後
python gate_checker/gate_check.py --phase implementation --file tests/test_secret_scan.py
