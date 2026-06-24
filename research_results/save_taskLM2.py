import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
pending = os.path.join(base, "pending_tasks")

# Task L
task_l_path = os.path.join(pending, "20260619_200000_taskL_classify_fix.md")
with open(task_l_path, 'w', encoding='utf-8') as f:
    f.write(open(os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "research_results", "save_taskLM.py"), encoding='utf-8').read().split("task_l = r")[1].split('task_m = r')[0].strip().strip('"').strip("'").strip('"""'))

# fallback: just write the files directly
with open(task_l_path, 'w', encoding='utf-8') as f:
    f.write("# Task L - see chat for full content\n# placeholder")

print("Writing files with simpler approach...")

# Task L content
task_l_content = """# 【Cursor作業指示】Task L: 分類精度改善（other→project漏れ修正）【最優先】

対象ディレクトリ: ses_work/
作業内容: analyze_final.pyのルール分類を強化し、案件メールのother漏れを修正
完了条件: 下記テストケース全パス + 既存テスト全パス

緊急度: 高。141件の案件メールがother判定でNotion未登録になっている。

## 問題の全容

379件がother判定。内訳:
- 件名に案件含む: 141件 → 本来project
- 件名に要員/人材含む: 132件 → 本来skip
- その他: 106件 → ほぼ全部案件（単価・期間・勤務地表記から明らか）

## 原因

analyze_final.pyのPROJECT_PATTERNSが明確なプレフィックスしか拾えない。
SES業界で一般的な以下パターンが未対応:
1. 案件配信/案件募集 → unknownになる
2. 〜65万円等の単価表記 → engineer誤判定→skip
3. 7月〜/即日〜等の期間表記 → unknown
4. 募集/常駐/リモート/面談N回 → unknown

## 修正方針

### 1. classify_by_rule()にPROJECT優先判定を追加

件名に以下のキーワードがあればengineerより先にproject判定:
- 案件/募集/常駐/増員/面談/準委任/業務委託/決済者直/元請

単価表記+期間表記の組み合わせもproject:
- 単価: [0-9]{2,3}万 のパターン
- 期間: [0-9]月〜 や 即日〜

スコアリング: project_keyword + has_price + has_period >= 2 ならproject

### 2. AI分類のother判定を再チェック

classify_email_v2でAIがotherを返した場合、
件名に案件キーワードがあればprojectに昇格させる。

### 3. other再分類バッチ

raw_inbox.pyに reset_other_for_reclassify() を追加:
other判定かつ件名に案件キーワードを含むレコードのprocessed=0にリセット。
修正後のルールで再分類される。

## テストケース

- 【案件配信】7月〜/UiPath案件 → project
- 【フルリモート/〜65万円/TypeScript】AI開発 → project
- 決済者直【C/C++/常駐】→ project
- 【8月開始】購買管理PL/SQL募集（4名）→ project
- ★フルリモート!【Go / 80万〜90万】EC開発 → project
- 【SES交流会】つながりが次の案件をつくる → skip
- 【イルミナ：要員】M.N（29歳）→ skip
- 【BTM案件】Go/基本リモート → project
- お世話になっております → unknown

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
- Recall最優先: 案件を見落とすよりskipすべきものをprojectにする方がマシ
"""

task_m_content = """# 【Cursor作業指示】Task M: gate_checker Gemini→Claude Sonnet差替え

対象ディレクトリ: ses_work/gate_checker/
作業内容: 第2レビュアーをGemini→Claude Sonnet 4.6に変更
完了条件: Sonnet呼び出し成功 + テスト

## 背景
Gemini 2.0 Flashの無料枠が完全枯渇（quota=0）。
gate_checkerが実質GPT-4o単独判定になっている。

## 修正箇所

### 1. Gemini呼び出しをSonnet呼び出しに差し替え
- model: claude-sonnet-4-6-20250514
- API: https://api.anthropic.com/v1/messages
- ANTHROPIC_API_KEY環境変数を使用
- CostGuard統合: block_type=gate_checker, phase=review_sonnet

### 2. システムプロンプト改善（GPT/Sonnet両方）
以下を追加:
- CostGuardはLLM API専用。Notion/freee/LINE等は対象外
- Notion DBの読み書きは自動送信に該当しない
- 承認済み仕様変更（soft-skill all-pass、語彙外REVIEW化等）はNG判定しない

### 3. DAILY_CALL_LIMIT
10 → 30に修正（SPEC.md準拠）

### 4. ラベル更新
gemini_verdict → sonnet_verdict（結果JSON含む）

## テスト
- Sonnet呼び出し成功
- CostGuardでコスト記録
- DAILY_CALL_LIMIT=30反映

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

with open(os.path.join(pending, "20260619_200000_taskL_classify_fix.md"), 'w', encoding='utf-8') as f:
    f.write(task_l_content)
print("saved: taskL")

with open(os.path.join(pending, "20260619_200100_taskM_sonnet_gate.md"), 'w', encoding='utf-8') as f:
    f.write(task_m_content)
print("saved: taskM")

for fn in sorted(os.listdir(pending)):
    if fn.startswith('2026'):
        print(f"  {fn}")
