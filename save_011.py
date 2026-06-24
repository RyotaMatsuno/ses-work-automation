# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

task = """# 【Cursor作業指示】mail_pipeline 件名キーワード事前分類でコスト削減

対象: ses_work/mail_pipeline/mail_pipeline.py
優先度: P0（コスト直結）
根拠: 1日4,580件のメールを全件処理するとLLMコストが月$300超。件名キーワードで事前分類しLLM呼び出しを80%削減する（2026-06-15 調査確定）

---

## 背景・現状の問題

1. sessalesに1日4,454件、合計4,580件のメールが届く
2. 現在FETCH_LIMIT=200で最新200件しか処理できず、カバー率4.5%
3. mail_pipelineは1通あたりLLMを2〜4回呼ぶ（分類+抽出+ダブルチェック）
4. 全件処理すると月$300〜400、コール数1,800/日（再試行込み）

## ゴール

件名のキーワードパターンで事前分類し、LLMを「判断が難しいメールだけ」に絞る。
- 明確に非案件（請求書・注文書等）→ LLMゼロでスキップ
- 明確に案件（【BTM案件】【案件情報】★★★等）→ LLMゼロでproject判定、詳細抽出のみLLM
- 明確に人材（【弊社社員】【要員】【ご紹介】等）→ LLMゼロでengineer判定、詳細抽出のみLLM
- 判断不能なものだけ → 従来通りLLM分類

目標: LLM分類呼び出しを80%削減 → 月$80前後で全件（4,580件/日）処理

---

## タスク1: 件名キーワード分類関数を追加

ses_work/mail_pipeline/mail_pipeline.py に新規関数を追加する。

```python
# 件名キーワード事前分類（LLM不使用）
# 戻り値: "project" | "engineer" | "skip" | None(判断不能→LLMへ)

# 非案件（業務書類・事務メール）→ skip
SUBJECT_SKIP_PATTERNS = [
    "請求書", "注文書", "発注書", "見積書", "見積もり", "御見積",
    "納品書", "領収書", "勤務表", "勤怠", "稼働報告", "工数",
    "契約書", "覚書", "基本契約", "業務委託契約", "秘密保持",
    "支払", "入金", "振込", "口座", "押印", "捺印",
    "年末調整", "源泉", "インボイス", "適格請求書",
    "セミナー", "ウェビナー", "イベント", "勉強会", "登壇",
    "メンテナンス", "障害", "復旧", "アップデート通知",
    "おめでとう", "新年", "年始", "年末", "夏季休業", "休業",
    "アンケート", "ニュースレター", "メルマガ", "配信停止",
]

# 明確に案件 → project（詳細抽出のみLLM）
SUBJECT_PROJECT_PATTERNS = [
    "案件", "募集", "求人", "案件情報", "BP案件",
    "★案件", "■案件", "【案件",
    "／", "@", "万円", "万／",  # SES案件件名の典型パターン
    "リモート", "常駐", "週", "月〜", "即日",
    "PMO", "PM補佐", "SE", "PG", "インフラ案件",
]

# 明確に人材 → engineer（詳細抽出のみLLM）
SUBJECT_ENGINEER_PATTERNS = [
    "弊社社員", "弊社正社員", "弊社プロパー", "弊社フリーランス",
    "弊社エンジニア", "弊社技術者", "自社社員",
    "要員", "人材", "技術者のご紹介", "エンジニアのご紹介",
    "ご紹介", "経歴書", "スキルシート", "プロパー",
    "営業中", "提案situation", "稼働可能",
]


def classify_subject_keyword(subject: str) -> str | None:
    \"\"\"件名キーワードで事前分類。LLM不要。判断不能はNoneを返す。\"\"\"
    if not subject:
        return None
    s = subject

    # 1. スキップ判定を最優先（業務書類）
    for kw in SUBJECT_SKIP_PATTERNS:
        if kw in s:
            return "skip"

    # 2. 人材判定（弊社社員・要員・ご紹介などは人材確度が高い）
    eng_hit = sum(1 for kw in SUBJECT_ENGINEER_PATTERNS if kw in s)

    # 3. 案件判定
    prj_hit = sum(1 for kw in SUBJECT_PROJECT_PATTERNS if kw in s)

    # 明確にどちらか一方に寄っている場合のみ確定（誤判定を避ける）
    if eng_hit >= 1 and eng_hit > prj_hit:
        return "engineer"
    if prj_hit >= 2 and prj_hit > eng_hit:  # 案件は2つ以上ヒットで確定（厳しめ）
        return "project"

    # 判断不能 → LLMに委ねる
    return None
```

## タスク2: classify_email_v2 のフローに組み込む

現在のclassify_email_v2は内部で analyze_final.classify_by_rule を呼んでいる。
その前段に classify_subject_keyword を追加する。

main()の処理ループ、またはclassify_email_v2内で以下のように分岐:

```python
# 件名キーワードで事前分類
kw_type = classify_subject_keyword(em.get("subject", ""))
if kw_type == "skip":
    # LLM呼ばずに即スキップ
    results[idx] = {"type": "other", "note": "件名キーワードskip"}
    continue
elif kw_type in ("project", "engineer"):
    # 分類はスキップ、詳細抽出のみLLM（extract_requestを直接積む）
    batch_requests.append(build_extract_request(f"extract_{kw_type}_{idx}", subject, body, kw_type))
    continue
# kw_type is None → 従来通りLLM分類へ
```

## タスク3: FETCH_LIMITとCLASSIFY_LIMITを引き上げ

mail_pipeline.py の設定値を変更:
```python
FETCH_LIMIT = 1500      # 200→1500（1アカウント最大1500件取得）
CLASSIFY_LIMIT = 1500   # 150→1500（分類上限も引き上げ）
```

理由: キーワード分類でLLM呼び出しが減るので、件数を増やしてもコストが抑えられる。

## タスク4: 実行頻度を30分→1日3回に変更（タスクスケジューラ）

現在30分おき（48回/日）の実行を、朝昼晩の3回に変更してコスト平準化:

```python
import subprocess
# 既存のmail_pipelineタスクを確認
subprocess.run(["schtasks","/query","/tn","SES_MailPipeline","/fo","LIST"], check=False)

# 削除して3回/日で再作成（8:30, 13:00, 18:00）
subprocess.run(["schtasks","/delete","/tn","SES_MailPipeline","/f"], check=False)
for t in ["08:30","13:00","18:00"]:
    subprocess.run([
        "schtasks","/create","/tn",f"SES_MailPipeline_{t.replace(':','')}",
        "/tr", r'cmd.exe /c "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\run_mail_pipeline.bat"',
        "/sc","DAILY","/st",t,"/ru","ma_py","/f"
    ], check=True)
```

※ run_mail_pipeline.batの存在を確認すること。なければ既存の実行batファイル名を使う。

## タスク5: コスト試算ログを追加

main()の最後に、その実行で使ったLLMコール数とキーワードスキップ数をログ出力:
```python
log(f"[コスト効率] LLM分類: {llm_classify_count}件 / キーワードスキップ: {kw_skip_count}件 / キーワード確定: {kw_decided_count}件")
```

---

## テスト方法

```
cd ses_work
python -c "from mail_pipeline.mail_pipeline import classify_subject_keyword; print([classify_subject_keyword(s) for s in ['【BTM案件】【AWS】Max73万', '【弊社社員】Java経験8年', '7月分御見積書のご送付', 'セミナーのご案内']])"
```
期待される出力: ['project', 'engineer', 'skip', 'skip']

その後ドライランで全体動作確認:
```
python -m mail_pipeline.mail_pipeline --dry-run
```
ログに「[コスト効率]」行が出て、キーワードスキップ・確定件数が表示されればOK。

---

## ゲート

実装完了後、gate_checkerでレビュー:
```
python gate_checker/gate_check.py --phase implementation --file mail_pipeline/mail_pipeline.py
```

GO判定後、本番のタスクスケジューラを更新。

完了後「メールキーワード分類完了」とClaude.aiに報告すること。
"""

path = os.path.join(PENDING, "011_mail_keyword_classify.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 011_mail_keyword_classify.md")
print(f"pending_tasks: {sorted(os.listdir(PENDING))}")
