# git pre-pushシークレットスキャンフック導入（再発防止）

背景: 2026-07-06、GitHub Push ProtectionがOpenAIキー（research_results一時スクリプト）と
GCPキー（gate_checker/resultsレビューログ）の混入pushをブロック。ローカルで事前検知する層を追加する。

## 実装（scripts/secret_scan.py 新規 + .git/hooks/pre-push）

1. scripts/secret_scan.py:
   - 対象: push対象コミット範囲の追加blob（git diff origin/main..HEAD --name-only ベース）
   - パターン: sk-[A-Za-z0-9_\-]{20,} / AIza[0-9A-Za-z_\-]{30,} / -----BEGIN.*PRIVATE KEY /
     ya29\. / LINEチャネルトークン形式（英数+/=の140字以上連続）
   - バイトレベル検査（UTF-16の\x00混在パターンも対応。schtasks_all.txtで実証済みの盲点）
   - ヒット時: ファイル名と行番号のみ表示（**値は絶対に表示しない**）、exit 1
2. .git/hooks/pre-push: python scripts/secret_scan.py を呼ぶ薄いラッパー（.batではなくsh形式、Git for Windows対応）
3. hooksはclone時に消えるため、scripts/install_hooks.py も作成しREADMEに1行追記

## テスト（tests/test_secret_scan.py）
- 各パターンの検知 / UTF-16混在の検知 / 値がstdoutに出ないこと

## 完了後
python gate_checker/gate_check.py --phase implementation --file scripts/secret_scan.py
※ ゲートは7/7以降に実行（7/6は日次上限到達済み）

## 禁止事項
- config/.env等のignore済みファイルを検査対象にしない（誤検知でpush不能になるため対象はpush差分のみ）
- LLM呼び出し不要（ルールベースのみ）
