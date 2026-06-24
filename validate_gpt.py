import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
sys.path.insert(0, str(base / "matching_v3"))
sys.path.insert(0, str(base))

from structurer import structure

from config import Config
from cost_guard import CostGuard

cfg = Config()
cg = CostGuard()

# ========== 精度テスト: 実際の案件メール5パターン ==========
test_cases = [
    {
        "name": "標準案件（必須/尚可明確）",
        "body": """
Java/SpringBootエンジニア募集
【業務内容】金融系Webアプリのバックエンド開発
【必須】Java5年以上、Spring Boot、Oracle SQL
【尚可】AWS、Docker、マイクロサービス
【単価】70〜75万円
【期間】2026年7月〜長期
【勤務地】渋谷（週3リモート可）
【面談】2回
【外国籍】不可
""",
        "expect": {"required": ["Java", "Spring Boot", "Oracle SQL"], "price_min": 70, "price_max": 75, "remote": True},
    },
    {
        "name": "単価のみ上限記載",
        "body": """
PMO支援 〜60万円
要件定義〜基本設計の上流工程経験必須
プロジェクト管理ツール（JIRA/Confluence）使用経験
勤務地: 大手町 フルリモート不可
期間: 即日〜6ヶ月
面談1回
""",
        "expect": {"price_max": 60, "price_min": None, "remote": False},
    },
    {
        "name": "面談日時指定あり",
        "body": """
Pythonエンジニア急募
必須: Python3年以上、Django、PostgreSQL
単価: 55万円固定
面談: 6/10(水) 14:00 オンライン確定
勤務地: 全国どこでもOK（フルリモート）
開始: 即日
""",
        "expect": {"price_min": 55, "price_max": 55, "interview_scheduled": True, "remote": True},
    },
    {
        "name": "スキルが曖昧な案件",
        "body": """
ITコンサルタント募集
コミュニケーション能力が高い方
主体性・当事者意識のある方
上流から一気通貫で対応できる方
単価応相談
東京都内 出社あり
""",
        "expect": {"required": [], "ambiguous": True, "price_min": None},
    },
    {
        "name": "高単価SE案件",
        "body": """
【急募】インフラエンジニア
必須: AWS(3年以上)、Terraform、Linux
尚可: GCP、Kubernetes、CI/CD
単価: 80〜90万円
期間: 2026年8月〜
勤務地: 品川（リモート週4可）
面談2回（1回目技術確認、2回目役員）
外国籍: 相談可
""",
        "expect": {"price_min": 80, "price_max": 90, "required": ["AWS", "Terraform", "Linux"]},
    },
]

results = []
total_input = 0
total_output = 0
total_cost = 0.0

print("=" * 60)
print("【精度テスト】5ケース")
print("=" * 60)

for tc in test_cases:
    start = time.time()
    try:
        result = structure(tc["body"], cg, cfg)
        elapsed = time.time() - start

        # コスト計測（usage_tracker/cost_log.jsonlの最新行から取得）
        cost_log = base / "usage_tracker" / "cost_log.jsonl"
        last_cost = 0.0
        last_in = last_out = 0
        if cost_log.exists():
            lines = cost_log.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                last = json.loads(lines[-1])
                last_cost = float(last.get("cost_usd", 0))
                last_in = int(last.get("input_tokens", 0))
                last_out = int(last.get("output_tokens", 0))
        total_cost += last_cost
        total_input += last_in
        total_output += last_out

        # 精度チェック
        issues = []
        exp = tc["expect"]
        if "price_min" in exp:
            if exp["price_min"] is None:
                if result.get("price_min") is not None:
                    issues.append(f"price_min: got {result.get('price_min')} expected None")
            else:
                if result.get("price_min") != exp["price_min"]:
                    issues.append(f"price_min: got {result.get('price_min')} expected {exp['price_min']}")
        if "price_max" in exp:
            if result.get("price_max") != exp["price_max"]:
                issues.append(f"price_max: got {result.get('price_max')} expected {exp['price_max']}")
        if "required" in exp:
            got_req = [s.lower() for s in result.get("required_skills", [])]
            for skill in exp["required"]:
                if skill.lower() not in got_req:
                    issues.append(f"missing required skill: {skill}")
        if "remote" in exp:
            remote_ok = result.get("remote_ok") not in [None, "none", "no", False]
            if remote_ok != exp["remote"]:
                issues.append(f"remote_ok: got {result.get('remote_ok')} expected {exp['remote']}")
        if "interview_scheduled" in exp:
            has_sched = result.get("interview_scheduled_at") is not None
            if has_sched != exp["interview_scheduled"]:
                issues.append(f"interview_scheduled_at: got {result.get('interview_scheduled_at')}")
        if "ambiguous" in exp and exp["ambiguous"]:
            if len(result.get("required_skills", [])) > 0:
                issues.append(f"曖昧案件なのにrequired_skillsに値: {result.get('required_skills')}")

        status = "OK" if not issues else f"WARN({len(issues)}件)"
        print(f"\n[{status}] {tc['name']} ({elapsed:.1f}s, in={last_in} out={last_out} ${last_cost:.5f})")
        for iss in issues:
            print(f"  ⚠ {iss}")
        if not issues:
            req = result.get("required_skills", [])
            opt = result.get("optional_skills", [])
            amb = result.get("ambiguous_skills", [])
            print(f"  required={req}")
            print(f"  optional={opt}")
            print(f"  ambiguous={amb}")
            print(
                f"  price={result.get('price_min')}〜{result.get('price_max')}万 remote={result.get('remote_ok')} interview_at={result.get('interview_scheduled_at')}"
            )
        results.append({"name": tc["name"], "ok": not issues, "issues": issues})

    except Exception as e:
        print(f"\n[ERROR] {tc['name']}: {e}")
        results.append({"name": tc["name"], "ok": False, "issues": [str(e)]})

print("\n" + "=" * 60)
print("【コスト集計】")
print("=" * 60)
print(f"  5ケース合計: in={total_input} out={total_output} tokens")
print(f"  5ケース合計コスト: ${total_cost:.5f}")
print(f"  1ケース平均: ${total_cost / 5:.5f}")
# 730回/日推計
daily_est = (total_cost / 5) * 730
print(f"  730回/日 推計: ${daily_est:.3f}/日 → 月(22営業日)${daily_est * 22:.2f}")
# Haiku比較
haiku_daily = 0.25  # 旧推計
print(f"  Haiku比較: ${haiku_daily:.2f}/日 → GPT-4o-mini ${daily_est:.3f}/日")
ok_count = sum(1 for r in results if r["ok"])
print(f"\n精度: {ok_count}/{len(results)} ケースOK")
