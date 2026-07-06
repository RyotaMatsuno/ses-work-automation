#!/usr/bin/env python3
"""GPT-5.4 壁打ち: matching_v3 商用品質化 — 10ラウンド"""
import sys, json, time, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
from pathlib import Path

API_KEY = os.environ.get("OPENAI_API_KEY") or Path("config/.env").read_text(encoding="utf-8").split("OPENAI_API_KEY=")[1].split("\n")[0].strip().strip('"')
URL = "https://api.openai.com/v1/responses"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

CONTEXT = """
# SESマッチングシステム matching_v3 — 商用品質化の壁打ち

## 事業概要
- SES（システムエンジニアリングサービス）人材紹介事業
- エンジニアDB: 208名、案件DB: 7,757件
- 商用品質目標: Recall@10 >= 85%, Precision@10 >= 40%
- 現状: 本番avg_matches=0.2（実質マッチゼロ）

## 現在のアーキテクチャ（Phase 6: 3層フィルタ）
1. Hard Filter: 提案対象フラグ=False除外、稼働中除外、3ヶ月超遅延除外
2. Soft Scoring: skill(0.5) + location(0.15) + experience(0.15) + availability(0.2)
3. Rerank: total_score降順でTop100 → judge_with_meta()でMATCH/REVIEW/NG判定

## judge_with_meta() の処理フロー
1. must_not条件チェック（外国籍不可、年齢制限）
2. 単価・粗利チェック（最低5万、最高15万）
3. 必須スキルから soft_skills（コミュ力等26件）を除外
4. 必須スキルから process_skills（要件定義、基本設計等163件）を「competencies」として分離 → マッチング対象外
5. 残った技術スキルのみでエンジニアDBとマッチング
6. 並行スコアチェック（5.0以上NG）
7. 鮮度チェック（21日超NG）

## 発見された根本問題

### 問題1: process_skills除外が致命的（最大原因の仮説）
process_skills.json に163件登録。以下がマッチング対象外:
- 要件定義、基本設計、詳細設計、インフラ設計、運用保守、テスト、設計、実装、開発
- AWS設計構築、インフラ構築、Webアプリケーション開発、etc.
→ 案件が「Java + 要件定義経験」を求めても、「要件定義」は除外され「Java」だけでマッチ
→ Java持ちなら誰でもマッチするか、Javaすら持っていなければ0件

### 問題2: コンピテンシー（工程経験）がエンジニアDBに未登録
- 案件側: 「基本設計」23件、「要件定義」18件、「リーダー経験」14件が必須スキル
- エンジニアDB: これらのフィールドが存在しない。技術スキル（Java/AWS等）のみ
- bio/notesには「基本設計から対応可能」等の記述が164/208名にあるが未構造化

### 問題3: スキル語彙の不一致（0件率60.6%）
- 案件側のスキル名とエンジニアDB側のスキル名が一致しない
- alias辞書で715→487に正規化済みだが、まだOOV（辞書外）が多い
- 例: 「springboot」(案件) vs 「Spring Boot」(辞書) — 正規化ヒットしない

### 問題4: CostGuard日次上限到達
- 6/29ログ: 処理=27件で上限到達、残り803件スキップ
- structurer（案件構造化）にgpt-4.1-nanoを使用、1案件=数百トークン消費
- 日次$8上限が830件の案件ボリュームに対して不足

### 問題5: structured.jsonlにゴミデータ3.3%
- '1~5への適合状況(〇' 等のメール本文断片がスキルとして登録

### 問題6: Engineer単価未設定（推定が実態と乖離）
- 単価未設定エンジニアは推定単価で粗利計算 → 実際と乖離してNG判定される可能性

## 改善仮説（現時点）

A. process_skills.jsonの抜本見直し — 除外ではなく「技術×工程」の2軸マッチングに変更
B. エンジニアDBにコンピテンシー列追加 — bio/notesからLLM抽出（164/208名に情報あり）
C. エイリアス辞書大幅拡充 — OOVスキルの自動検出→辞書追加パイプライン
D. CostGuard上限引き上げ or structurerのLLM不要化（ルールベース構造化率向上）
E. ゴミフィルタ強化（denylist拡充）
F. 2軸マッチング導入後の精度評価フレームワーク構築

## 質問
あなたはdevil's advocateとして、上記分析と改善仮説を厳しく検証してください。
- 見落としている問題はないか？
- 改善仮説の優先順位は正しいか？
- 実装リスクや副作用は？
- 商用品質（Recall@10>=85%, Precision@10>=40%）達成に何が足りないか？
"""

ROUNDS = [
    # Round 1: 全体分析
    {"role": "Devil's Advocate — 全体分析", "prompt": CONTEXT},
    # Round 2: process_skills問題の深掘り
    {"role": "工程スキル設計の専門家", "prompt": "Round 1の指摘を踏まえて。process_skills.jsonの163件を除外する現設計は本当に間違いか？SES業界では「Java経験5年」と「基本設計経験」は別軸で評価する。除外ではなく2軸化する場合、具体的にどう実装すべきか？エンジニアDBに工程レベル（PG/SE/上級SE）を追加するのと、スキル×工程のマトリクスを持つのと、どちらが良いか？"},
    # Round 3: エンジニアDB品質
    {"role": "データ品質エンジニア", "prompt": "Round 2の議論を踏まえて。164/208名のbio/notesからLLM抽出してコンピテンシーを構造化する提案がある。(1)抽出精度はどの程度見込めるか？(2)hallucination対策は？(3)208名×LLM呼び出しのコストは？(4)定期更新の仕組みは？(5)手動レビューは必要か？"},
    # Round 4: 精度評価フレームワーク
    {"role": "ML評価の専門家", "prompt": "Round 3を踏まえて。Recall@10>=85%, Precision@10>=40%を測定するには正解データ（ground truth）が必要。(1)208名×7757件の全組合せは不可能。どうサンプリングするか？(2)正解ラベルは誰がつけるか？CEO松野のドメイン知識に依存？(3)オフライン評価とオンライン評価の使い分けは？(4)A/Bテストは可能か？"},
    # Round 5: CostGuard問題
    {"role": "コスト最適化エンジニア", "prompt": "Round 4を踏まえて。CostGuard日次$8で830件処理は無理。(1)structurerのルールベース化で何%のLLM呼び出しを削減できるか？(2)メール本文からの構造化はルールベースでどこまで可能か？(3)LLMを使う場合gpt-4.1-nanoで十分か？(4)$8→$15に上げるべきか？(5)案件の優先度フィルタ（個別送信案件のみ処理等）は有効か？"},
    # Round 6: エイリアス辞書
    {"role": "NLP/語彙正規化の専門家", "prompt": "Round 5を踏まえて。715→487の正規化で32%削減済み。OOVスキルの自動検出→辞書追加パイプラインを作る場合: (1)未知スキルの検出ロジックは？(2)自動追加の安全性は？誤統合のリスクは？(3)Java≠JavaScript等の誤統合防止リストは十分か？(4)バージョン付きスキル（Java 17, Python 3.11）の扱いは？(5)略語（k8s=Kubernetes）の網羅は？"},
    # Round 7: 実装ロードマップ
    {"role": "テックリード", "prompt": "Round 1-6の全議論を踏まえて。商用品質達成のための実装ロードマップを提案してください。(1)Phase分割と依存関係 (2)各Phaseの工数見積もり（Cursor実装前提）(3)最もROIが高い順序 (4)並列実行可能なタスク (5)リスクと回避策 (6)各Phase完了後の期待精度"},
    # Round 8: 副作用とリグレッション
    {"role": "QAエンジニア", "prompt": "Round 7のロードマップに対して。各変更が既存の動作に与える副作用を洗い出してください。(1)process_skills除外をやめると、ノイズマッチが増えないか？(2)コンピテンシー抽出の誤りがfalse positiveを生まないか？(3)エイリアス拡充で意図しないマッチが増えないか？(4)CostGuard上限変更のリスクは？(5)テスト戦略は？"},
    # Round 9: SES業界特有の考慮
    {"role": "SES営業10年のベテラン", "prompt": "Round 1-8の技術的議論を踏まえて、SES業界の実務観点から。(1)「要件定義経験」は本当に必須か？書いてあっても面談では柔軟に見る企業が多くないか？(2)単価交渉で5万円の幅がある中で、マッチングの単価フィルタはどの程度厳密にすべきか？(3)「並行3件で提案NG」は厳しすぎないか？(4)鮮度21日は短すぎないか？1ヶ月にすべきか？(5)面談通過率3割前提で、提案数を増やす方が成約率向上に効くのではないか？"},
    # Round 10: 最終結論
    {"role": "総括 — 最終判断", "prompt": "Round 1-9の全議論を総合して、以下を最終結論として出してください:\n1. 商用品質達成に必要な改善の優先順位（Top 5）\n2. 各改善の期待インパクト（定量）\n3. 実装順序とタイムライン\n4. 松野CEOに報告すべき最重要3点\n5. 見送るべき改善とその理由"}
]

results = []
conversation_history = ""

for i, round_info in enumerate(ROUNDS):
    round_num = i + 1
    print(f"\n{'='*60}")
    print(f"Round {round_num}/10: {round_info['role']}")
    print(f"{'='*60}")

    if round_num == 1:
        user_msg = round_info["prompt"]
    else:
        user_msg = f"これまでの議論:\n{conversation_history}\n\n---\nRound {round_num} ({round_info['role']}):\n{round_info['prompt']}"
        # Truncate if too long
        if len(user_msg) > 30000:
            user_msg = user_msg[-28000:]

    payload = {
        "model": "gpt-5.4",
        "input": [{"role": "user", "content": user_msg}],
        "instructions": f"あなたは{round_info['role']}です。日本語で簡潔に回答。箇条書き推奨。結論を先に述べてから根拠を示す。曖昧な表現は避け、具体的な数字と実装案を出す。",
        "reasoning": {"effort": "low"},
        "max_output_tokens": 3000,
    }

    try:
        resp = requests.post(URL, headers=HEADERS, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        answer = ""
        for block in data.get("output", []):
            if block.get("type") == "message":
                for content in block.get("content", []):
                    if content.get("type") == "output_text":
                        answer = content["text"]
        
        if not answer:
            answer = str(data)
        
        print(f"\n{answer[:2000]}")
        if len(answer) > 2000:
            print(f"\n... (truncated, full={len(answer)} chars)")
        
        results.append({
            "round": round_num,
            "role": round_info["role"],
            "answer": answer
        })
        conversation_history += f"\n\n## Round {round_num} ({round_info['role']}):\n{answer[:3000]}"
        
    except Exception as e:
        print(f"ERROR: {e}")
        results.append({"round": round_num, "role": round_info["role"], "answer": f"ERROR: {e}"})

    time.sleep(1)

# Save results
output_path = Path("matching_v3/research_results/wallhit_commercial_quality_20260630.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n\n{'='*60}")
print(f"壁打ち完了。結果: {output_path}")
print(f"{'='*60}")
