【Cursor作業指示】line_query engineer_query バグ修正
対象ファイル: ses_work/line_query/line_query.py
完了条件:
  1. engineer_query() に稼働状況フィルタが追加されている
  2. 案件の最終更新フィルタが 4営業日 → 正しい値になっている
  3. python -m py_compile line_query/line_query.py が通る

━━━ 背景 ━━━
「PH 京成小岩」形式のLINEオンデマンドマッチングで「マッチ案件なし」が返ってくるバグ。
調査の結果 engineer_query() に稼働状況フィルタが抜けているのが原因と特定。
project_query() には正しくフィルタがある（稼働可能 or 調整中）のに、
engineer_query() にはそれがない。

━━━ 修正内容（1箇所） ━━━

【修正】engineer_query() 内の matched_engineers の生成部分に稼働状況フィルタを追加

変更前:
    matched_engineers = [
        e for e in engineers
        if _match_initial(e, initial) and _match_station(e, station)
    ]

変更後:
    matched_engineers = [
        e for e in engineers
        if _match_initial(e, initial)
        and _match_station(e, station)
        and _select_prop(e, PROP_WORKST) in (VAL_ACTIVE2, VAL_ADJUSTING)
    ]

※ VAL_ACTIVE2 = '稼働可能'、VAL_ADJUSTING = '調整中'、PROP_WORKST = '稼働状況'
　 これらは同ファイル内で既に定義済みなのでimport不要。

━━━ 注意 ━━━
- ファイルはcp932エンコーディング。読み書きともに encoding='cp932' を使うこと
- 変更は上記1箇所のみ。他は一切触らない
- 変更後: python -m py_compile line_query/line_query.py で構文確認

━━━ ゲートチェック ━━━
python gate_checker/gate_check.py --phase implementation --file line_query/line_query.py


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
