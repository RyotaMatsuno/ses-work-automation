# GPT壁打ち: reclass枠starvationバグ
日時: 2026-06-19 21:30
モデル: GPT-5.4 (reasoning_effort=low)
壁打ち回数: 2回

## バグ概要
fetch_unprocessed_from_dbのreclass 20%枠が実行時にfreshに食われ、otherが402件未消化のまま滞留。

## 観測事実
- ログ: fresh:200/reclass:0 が17:00-20:00連続
- DB直叩き: fresh=160, reclass=40 が正しく取れる（シミュレーション正常）
- dict変換: classify_result='other'が正しく保持（検証済み）
- row_factory: sqlite3.Row設定済み
- insert_raw_email: UPSERTにclassify_result含まず（保護済み）
- 21:00時点: other 402→362（40件減少、reclass_quota=40と一致）

## GPT分析結果
### Round 1 (devil's advocate)
- 最有力: rows→dict変換でclassify_resultが欠落 → **検証の結果、否定**
- 推奨修正: fetch返り値をタプル化(fresh, reclass)で後段再判定廃止

### Round 2 (devil's advocate)
- 仮説3(UPSERT上書き): コード確認で **否定**（classify_resultはUPDATEに含まれない）
- 結論: 根本原因特定には実行時デバッグログが必要
- 最短デバッグ: _save前後のother/null件数 + fetch内SQL直後カウント + _main_body受取直後カウント

## 根本原因（未確定）
DB層・dict変換・UPSERT全て正常。しかし実行時にreclass:0になる原因不明。
可能性:
1. 実行タイミングでDBの状態が異なる（別プロセスの干渉等）
2. fetch_recent_emails直後の保存でDBの未処理freshが急増し何らかの方法でreclassが見えなくなる
3. パイプライン内の別コードパス（recovery mode等）が介入

## 合意修正方針
1. fetch_unprocessed_from_dbの返り値を(fresh_items, reclass_items)タプルに変更
2. 呼び出し側でclassify_resultからの再判定を廃止
3. デバッグログ追加（保存前後other/null件数、SQL直後カウント、受取直後カウント）
4. _save前後のotherカウントログ（仮説3の最終検証用）
