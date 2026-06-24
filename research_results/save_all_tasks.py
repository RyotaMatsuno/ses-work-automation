import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
pending = os.path.join(base, "pending_tasks")
os.makedirs(pending, exist_ok=True)

# Week1 Task A
task_a = """# 【Cursor作業指示】Week1 Task A: 即効バグ修正2件

対象ディレクトリ: ses_work/
作業内容: 案件取りこぼし＋全員マッチング対象化の即効修正
完了条件: 2件とも修正＋テスト追加＋既存テスト全パス
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: BTM/NBW案件のengineer誤判定→skip修正（最優先）

### 問題
mail_pipeline/analyze_final.py の ENGINEER_PATTERNS に 【BTM|【NBW があり、
【BTM案件】【NBW案件】など案件メールまでengineer判定→skipされている。

### 修正方針
analyze_final.py の該当パターンを修正:

変更前: 【BTM|【NBW
変更後: 【BTM要員|【BTM人材|【BTM】.*要員|【NBW要員|【NBW人材|【NBW】.*要員

さらに、件名に「案件」を含む場合はengineerパターンより先にproject判定する例外ルールを
classify_by_rule() の先頭に追加:
```python
if re.search(r'案件', subj):
    for pat in PROJECT_PATTERNS:
        if pat.search(subj):
            return "project"
```

### テスト追加
tests/test_analyze_final.py に以下テストケースを追加:
- 【BTM案件】Java開発 → project
- 【NBW案件】PMO → project
- 【BTM要員】Java/5年/男性 → skip（既存動作維持）
- 【BTM案件】要員ご紹介 → project（案件優先ルール確認）

---

## 修正2: Notion 400フォールバックで全員取得→処理中断に変更

### 問題
matching_v3/notion_client.py の get_active_engineers() で
Notion APIが400を返すとフィルタをスキップし全エンジニアを取得する。

### 修正方針
notion_client.py の get_active_engineers():

変更前:
```python
except Exception as e:
    log.warning(f"提案対象フラグフィルタ失敗: {e}")
    # フィルタなしで全件取得にフォールバック
```

変更後:
```python
except Exception as e:
    log.error(f"提案対象フラグフィルタ失敗 - マッチング中断: {e}")
    raise RuntimeError(f"提案対象フラグフィルタ利用不可のためマッチング中断: {e}") from e
```

matching_v3.py の呼び出し側で RuntimeError をキャッチし、
LINE通知（push_or_log経由）で松野に異常を通知して終了。

### テスト追加
- Notion API 400時にRuntimeErrorが発生すること
- get_active_engineers()がRuntimeError時にマッチングが中断すること

---

## 共通ルール
- 既存テスト全パス
- 新規コードにはtype hintを付けること
"""

# Week1 Task B
task_b = """# 【Cursor作業指示】Week1 Task B: Notion登録失敗リトライ＋processed管理修正

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: 案件データ永久欠損の防止
完了条件: 修正＋テスト追加＋既存テスト全パス
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: register_project()をcommon/notion_register.pyに委譲

### 問題
mail_pipeline.py の register_project() は429リトライなし・timeout未指定・重複チェックなし。
一方 common/notion_register.py には429リトライ＋upsertが実装済みだが未使用。

### 修正方針
1. mail_pipeline.py の register_project() 内のNotion API呼び出しを
   common.notion_register.register_project() に委譲
2. properties組み立てロジックは mail_pipeline.py に残す
3. 429リトライ、案件名+入力元でupsert、timeout=30s が自動適用される

---

## 修正2: Notion登録失敗時のprocessed管理修正

### 問題
finally節で無条件にsave_processed_id()を実行 → 登録失敗でもprocessed=1 → 再処理不可

### 修正方針
```python
notion_success = False
try:
    classify_result = classify_email_v2(...)
    update_classify_result(msg_id, classify_result)
    if classify_result == "project":
        notion_success = register_project(info, ...)
        if notion_success:
            # 後続処理
            ...
    else:
        notion_success = True
except Exception as e:
    log(f"処理エラー: {e}")
    import traceback
    log(traceback.format_exc())
finally:
    if notion_success:
        save_processed_id(msg_id)
    else:
        log(f"Notion登録未完了のため再処理対象: {msg_id}")
```

### 無限再処理ループ防止
raw_inbox.py に retry_count カラム追加。
retry_count >= 3 の場合は processed=1 にして諦める（ログ+LINE通知）。

### テスト追加
- Notion登録成功時: processed=1
- Notion登録失敗時: processed=0（再処理対象）
- retry_count >= 3: processed=1 + 警告ログ

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

# Week2 Task C
task_c = """# 【Cursor作業指示】Week2 Task C: pipeline CostGuard v2統合

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: pipelineの全LLM経路をCostGuard v2に統合（CEO承認済み: fail-close方式）
完了条件: 全LLM呼び出しがCostGuard v2経由 + fail-close + テスト追加
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: call_claude()にCostGuard v2を統合

変更前: 独自$2/日制限（get_today_cost_usd）→ エラー時$0返却（暴走リスク）
変更後: CostGuard v2 の allowed() → finalize() を使用

```python
from common.cost_guard import allowed, finalize

def call_claude(prompt, system_prompt, max_tokens=1500):
    decision = allowed(
        block_type="mail_pipeline",
        phase="classify",
        estimated_input_tokens=len(prompt) // 4 + 200,
        estimated_output_tokens=max_tokens,
        model="claude-haiku-4-5-20251001"
    )
    if decision.exit_code != 0:
        log(f"CostGuard blocked: {decision.reason}")
        return ""
    try:
        response = client.messages.create(...)
        finalize(decision.claim_id, success=True,
                 actual_input_tokens=response.usage.input_tokens,
                 actual_output_tokens=response.usage.output_tokens)
        return response_text
    except Exception as e:
        finalize(decision.claim_id, transient=True)
        raise
```

## 修正2: Batch API経路にコスト記録追加
Batch完了後に record() でCostGuard v2に記録。投入前に allowed() でバジェット残量チェック。

## 修正3: 旧コスト管理コード削除
- get_today_cost_usd() → 削除
- DAILY_COST_LIMIT_USD = 2.0 → 削除
- log_cost() → CostGuard v2 の record() に置換

## テスト追加
- CostGuardブロック時にcall_claude()が空文字を返すこと
- Batch完了後にrecord()が呼ばれること
- 旧get_today_cost_usd()が存在しないこと

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
- CostGuard v2のインターフェースは変更しない
"""

# Week2 Task D
task_d = """# 【Cursor作業指示】Week2 Task D: 語彙外スキルREVIEW化 + importer修正

対象ディレクトリ: ses_work/
作業内容: マッチング精度改善 + importer安定化
完了条件: 修正＋テスト追加＋既存テスト全パス
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: 語彙外必須スキルのREVIEW化

### 問題
matcher.py の judge() で SkillNormalizer.normalize(skill) が None を返す語彙外スキル
（Terraform, SAP, Salesforce等 31件）はチェック対象外 → 必須不足でもMATCH化。

### 修正方針
```python
unknown_skills = []
for skill in required_skills:
    canonical = normalizer.normalize(skill)
    if canonical is None:
        unknown_skills.append(skill)
        continue
    if canonical not in engineer_skill_set:
        missing.append(skill)

if unknown_skills:
    reasons.append(f"語彙外必須スキル要確認: {', '.join(unknown_skills)}")
```

### テスト追加
- 必須「Terraform」（語彙外）→ REVIEW
- 必須「Java」+「SAP」→ JavaマッチかつSAPでREVIEW
- 全必須が語彙外 → REVIEW（NGではない）

---

## 修正2: importer exit 255修正

### 問題
mail_attachment_importer/importer.py が毎回途中クラッシュ。ログ不在。

### 修正方針
1. main()に最上位try/except追加（traceback出力）
2. ログファイルパスを明示設定
3. 処理件数カウンタ追加（何件目で落ちるか特定）
4. 各メール処理失敗は continue で全体を止めない

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト冒頭に
"""

# Week3 Task E
task_e = """# 【Cursor作業指示】Week3 Task E: soft-skill all-pass + Ruff/pyright導入

対象ディレクトリ: ses_work/
作業内容: (1)承認済みソフトスキル判定実装 (2)コード品質ツール導入
完了条件: soft-skill実装+テスト、ruff check/pyright basicが通ること
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: soft-skill all-pass実装

### 問題
承認済み方針「ヒューマン/ソフトスキルは全員○」が未実装。
PM/コミュ力等がambiguous_skillsとしてREVIEWトリガーか語彙外パスでMATCH化。

### 修正方針
1. config/soft_skills.json にソフトスキル一覧を定義:
   ["コミュニケーション", "リーダーシップ", "PM経験", "マネジメント", "折衝", "調整", ...]
2. matcher.py の judge() で必須スキル判定前にソフトスキルフィルタ:
   ソフトスキルに該当する必須は全員○（チェック対象外にする）
3. テスト: 必須「PM経験」→ 全員○（チェックしない）

---

## 修正2: Ruff + pyright導入

### 手順
1. pyproject.toml に以下を追加:
```toml
[tool.ruff]
target-version = "py312"
line-length = 120
[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]  # 段階的に解除

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

2. ruff check --fix . で既存コードを一括修正（動作は変わらない）
3. ruff format . で整形
4. pyright basic で型エラー数を記録（修正はしない、現状把握のみ）
5. .pre-commit-config.yaml を作成:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 注意
- 既存コードの型エラーは修正しない（数を記録するだけ）
- 新規コードにはtype hint必須のルールを維持
- ruff fixで動作が変わるケースがないか既存テストで確認

---

## 共通ルール
- 既存テスト全パス
"""

# Week3 Task F
task_f = """# 【Cursor作業指示】Week3 Task F: freee monthly退役 + FT階段粗利

対象ディレクトリ: ses_work/freee/
作業内容: (1)monthly無効化 (2)FT粗利ロジック修正
完了条件: monthly無効化確認 + FT粗利テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: freee_invoice_monthly.py 退役（CEO承認済み）

### 手順
1. Task Scheduler で SES_Freee_Invoice_Monthly を Disabled に変更
2. freee_invoice_monthly.py の先頭に以下を追加（安全装置）:
```python
print("このスクリプトは廃止されました。freee_invoice_v2.py を使用してください。")
sys.exit(0)
```
3. README/INFRA_SUMMARYを更新: monthly廃止、v2一本化

### 注意
- ファイルは削除しない（ロールバック用に残す）
- v2（freee_invoice_v2.py）が正常稼働していることを確認してから実施

---

## 修正2: FT階段粗利の実装

### 問題
コード上はFT粗利が一律68%。契約マスター（Google Sheets）には
9件→68%, 11件→75%, 14件→80% の階段が定義されているが未実装。

### 修正方針
1. freee_invoice_v2.py の粗利計算部分に契約マスターの件数参照ロジック追加
2. 契約マスター（Google Sheets ID: 1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI）
   からFT稼働件数を取得 → 階段テーブルで粗利率を決定
3. 階段テーブル:
   - 10件以下: 68%
   - 11-13件: 75%
   - 14件以上: 80%

### テスト追加
- FT 9件 → 68%
- FT 11件 → 75%
- FT 14件 → 80%

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

# Save all tasks
tasks = {
    "20260619_180000_week1_taskA_BTM_Notion400.md": task_a,
    "20260619_180100_week1_taskB_Notion_retry.md": task_b,
    "20260619_180200_week2_taskC_CostGuard_v2.md": task_c,
    "20260619_180300_week2_taskD_vocab_importer.md": task_d,
    "20260619_180400_week3_taskE_softskill_ruff.md": task_e,
    "20260619_180500_week3_taskF_freee_FT.md": task_f,
}

for fname, content in tasks.items():
    fpath = os.path.join(pending, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"saved: {fname}")

print(f"\n合計 {len(tasks)} タスクを pending_tasks/ に保存完了")
print(f"保存先: {pending}")

# List all pending tasks
print("\n--- pending_tasks/ 一覧 ---")
for f in sorted(os.listdir(pending)):
    size = os.path.getsize(os.path.join(pending, f))
    print(f"  {f} ({size:,} bytes)")
