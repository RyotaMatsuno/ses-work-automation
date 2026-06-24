import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())
from gate_checker.agreement_checker import _load_env, call_gemini, call_gpt4o_simple

env = _load_env()
openai_key = env.get("OPENAI_API_KEY", "")
gemini_key = env.get("GEMINI_API_KEY", "")

system_prompt = """あなたはSESビジネスのインフラ運用アドバイザーです。
コスト管理システムの設計判断を求められています。
事実関係を踏まえて、最適な対処方針を選んでください。
判定形式: 【推奨: A案】【推奨: B案】【推奨: C案】のいずれかを明示し、理由を3点以内で簡潔に。
"""

user_prompt = """## 背景
SES事業の自動化システムで、過去にコスト暴走事件が発生した（$50.88/日の損害）。
原因は .env の上限値が誤って $1/$6 になっていたこと。
現在は .env を $8/日・$140/月 に修正し、複数のシステムがこの値を参照する。

## コスト管理の二重構造

### レイヤー1: common/ledger.py（API呼び出し時のリアルタイム判定）
- mail_pipeline・matching_v3・line_bridge が利用
- .env から COST_GUARD_DAILY_USD / COST_GUARD_MONTHLY_USD を読む
- 現在: $8/日・$140/月（.envと一致）✅
- これを超えそうな場合は can_spend() が False を返し API呼び出しを止める

### レイヤー2: cost_guard.py（バッチ的な監視・Cloud Run強制停止）
- usage_tracker_daily から呼ばれる（5分おき）
- 上限値が **ハードコード**:
  - SOFT_DAILY_LIMIT = 0.8（ソフト警告）
  - HARD_DAILY_LIMIT = 1.5（Cloud Run の LLM_KILL=1 発動）
  - MONTHLY_LIMIT = 6.0（月次強制停止）
- これら3値は .env を一切読まない
- 今月累計が$2.61なので、あと$3.39で月次アラート発動
- 発動すると Cloud Run の line-webhook がAI機能停止

## 過去経緯
- 2026-06-10 に cost_guard.py の MONTHLY_LIMIT を 6.0 に下げた（暴走事件直後の保守的設定）
- 同日 .env も同じ値に下げた
- 後に .env だけ $140 に戻したが cost_guard.py の定数は$6のまま残った

## 検討案

### A案: cost_guard.py の定数を .env から読むよう変更
```python
MONTHLY_LIMIT = float(os.getenv("COST_GUARD_MONTHLY_USD", 6.0))
HARD_DAILY_LIMIT = float(os.getenv("COST_GUARD_DAILY_USD", 8.0))
SOFT_DAILY_LIMIT = HARD_DAILY_LIMIT * 0.5  # 50%で警告
```
- メリット: 設定の一元管理。.env変更だけで全システム同期
- デメリット: 暴走時の最終砦がレイヤー1と同じ値になり二重防護が薄れる

### B案: cost_guard.py をレイヤー1より厳しい独自値に保つ
```python
# .env: $8/日 $140/月（API呼び出し時の通常運用上限）
# cost_guard.py: $20/日 $300/月（明らかな暴走時の緊急停止ライン）
HARD_DAILY_LIMIT = 20.0
MONTHLY_LIMIT = 300.0
```
- メリット: 通常運用は$8/$140で動き、明らかな異常時のみ強制停止が発動する
- デメリット: 2系統の値を管理する必要

### C案: 段階的設計 - .env を本番想定値に近づける
```
.env: COST_GUARD_DAILY_USD=4.0 / MONTHLY_USD=50.0
cost_guard.py: HARD=8.0 / MONTHLY=140.0
```
- メリット: 通常運用を$4/$50に絞り保守的、最終砦も合理的な値
- デメリット: $50は実運用には足りない可能性（毎日$3使えば$93/月）

## 評価軸
1. 再発防止の確実性（最優先）
2. 通常運用の柔軟性
3. 設定の保守性（管理しやすさ）
4. 暴走時の被害最小化

## 質問
A・B・C のどれが最適か？
"""

print("=" * 60)
print("[GPT-4o]")
gpt = call_gpt4o_simple(system_prompt, user_prompt, openai_key)
print(gpt.text)
if gpt.error:
    print(f"[err: {gpt.error}]")

print("\n" + "=" * 60)
print("[Gemini]")
gem = call_gemini(system_prompt, user_prompt, gemini_key)
print(gem.text)
if gem.error:
    print(f"[err: {gem.error}]")
