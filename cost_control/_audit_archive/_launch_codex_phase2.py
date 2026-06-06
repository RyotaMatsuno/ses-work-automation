import subprocess, sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WD=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
CODEX=r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
LOG=os.path.join(WD,"cost_control","codex_phase2.log")

prompt=(
 "Phase 1は完了・コミット済みです。cost_control/SPEC.md と cost_control/TASKS.md を読み、"
 "今回は Phase 2（C4 配信スパム除外フィルタ / C5-1 案件自動失効スクリプト）のみを実装してください。"
 "【C4 配信フィルタ】mail_pipeline/mail_pipeline.py の取り込みで、分類API呼び出しの『前』に "
 "is_broadcast(msg)->bool を実装し、配信判定された案件メールは『分類スキップ＆Notion登録スキップ』にする（ログには残す）。"
 "重要: 実案件を絶対に誤除外しないこと。判定はヒューリスティック主体で、(a)List-Unsubscribe/List-Idヘッダ有り "
 "(b)本文フッタに『配信停止』『メルマガ』『一斉配信』等 (c)To/CCが多数宛て、のORで配信とみなす。"
 "送信元許可リストは任意機能とし、空でも動くこと（許可リストが空なら(a)(b)(c)のみで判定）。"
 "またfetch件数と分類件数を分離し、非配信の分類対象を1回あたり最大150件に制限する定数 CLASSIFY_LIMIT=150 を追加。"
 "【C5-1】新規 cost_control/project_expiry.py を作成。案件DB(343450ff-37c0-81e4-934e-f25f90284a3c)で "
 "ステータス=募集中 かつ created_time が4営業日より前 の案件を ステータス=終了 に更新する。"
 "営業日計算は jpholiday があれば使用、無ければ平日(土日除外)で近似。Notion REST直叩き(config/.envのNOTION_API_KEY)、"
 "ページネーション(page_size=100, has_more)、変更IDをログ出力。単体実行可能なスクリプトにする(後でジョブズがタスク登録する)。"
 "物理削除は禁止(ステータス変更のみ)。"
 "【厳守】送信系(メール送信・LINE push/reply・freee送信・成約フロー)に一切触れない。"
 "common/model_config.py と common/ledger.py(Phase1で作成済み)を再利用。モデル名の新規ハードコード禁止。"
 "各変更後 py_compile で構文確認し結果を cost_control_phase2_compile.txt に書く(stderr直読み禁止)。"
 "完了タスクのみ TASKS.md をチェック。Phase 3 には着手しない。最後に変更ファイル一覧と判定ロジック要約を出力。"
)
f=open(LOG,"w",encoding="utf-8")
f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} codex launch (Phase2)\n"); f.flush()
subprocess.Popen([CODEX,"exec",prompt,"-C",WD,"--dangerously-bypass-approvals-and-sandbox"],
                 stdout=f, stderr=subprocess.STDOUT, creationflags=0x08000000, cwd=WD)
print("codex Phase2 launched (background). log:", LOG)
