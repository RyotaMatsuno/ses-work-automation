#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MODEL_ROUTING.md 作成 (Cursor Pro $20運用 + 超過時フォールバック)"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

content = """# MODEL_ROUTING.md - モデル使い分け・超過時フォールバック運用

最終更新: 2026-06-16
確定者: ジョブズ + GPT-5.4 壁打ち + 実測値検証

---

## 1. 通常運用（確定: 2026-06-16）

### Cursor IDE経由のコード実装
- **モデル**: Claude Sonnet 4.6 (Cursor Auto / Composer 2.5 経由)
- **課金経路**: Cursor Pro $20/月 (月初の請求サイクル, 例: 6/9-7/9)
- **Cursor Pro含有枠**: Auto + Composer 枠 + API使用 $20分
- **使用率**: 線形換算で月末 ~26-30% 想定（74%余裕）
- **On-Demand Spending**: Disabled (超過時の自動課金OFF)
- **Anthropic API Key**: ON状態だが API used = 0% (Cursor Pro枠に内包)

### gate_checker系（OpenAI API直接呼出）
- **論点A確定値**: research/req/test/final_gate = gpt-5.4-mini / design/pre_impl = gpt-5.4 / implementation = gpt-5.3-codex
- **コスト管理**: common/ledger.py の CostGuard ($8/日, $140/月上限)
- **モデル経路**: OpenAI API 直接 (Cursorとは独立系統)
- **DAILY_CALL_LIMIT**: 30→60→90 段階解放
- **二次壁打ち**: design全件 / final_gate タグ判定 / implementation キーワード判定 (gpt-5.4-mini)

### 例外: 高難度の経営判断
- **モデル**: GPT-5.5 (年数回手動呼出)
- **発動条件**: 法人化・契約・税務・大規模アーキ変更 (Opus 4.8 モデル宣言と並走)

---

## 2. しきい値・監視

### Cursor Pro 含有枠監視
| しきい値 | アクション |
|---|---|
| 月中 50% 超 | 観察強化（Notion AI作業キューに記録） |
| 月中 70% 超 | 運用方針再確認（Pro+ アップグレード検討） |
| 月中 85% 超 | フォールバック発動判断 |
| 100% 到達 | On-Demand Disabled のため作業停止リスク |

### Anthropic Console 週次チェック (新規ルール)
- **頻度**: 週1回 (毎週月曜推奨)
- **対象URL**: https://console.anthropic.com
- **確認画面**: Usage / Daily Token Cost
- **異常値判定**: 1日 $10 超 = 即調査 (過去 $50.88/日 mail_pipeline インシデント前科)
- **将来自動化**: Anthropic Admin Key 取得 → ledger 連動 (TODO)

### OpenAI API (gate_checker系) 監視
- common/ledger.py が記録 (cost_state.json @ AppData/Local/ses_work_state/)
- CostGuard $8/日 / $140/月 上限で自動停止
- 装置1〜4 (フェーズ別超過警告・CostGuard停止時Notionキュー・ledger外挿検知・自動ロールバック) で多層防御

---

## 3. 超過時フォールバック手順

### Cursor Pro 含有枠 超過時 (Total 85%以上)
1. ジョブズが LINE で松野に通知
2. 当該日の Cursor 作業を一旦停止 (On-Demand Disabled のため Cursor 自体が止まる可能性)
3. 判断選択肢:
   - A. 当日終了 (翌日リセット待ち / 月末まで様子見)
   - B. Anthropic API Key OFF→ON 切替 + On-Demand 一時有効化
   - C. Pro+ ($60/月, 3倍枠) へアップグレード
4. **デフォルト推奨: A (翌日待ち)**。理由: 設計余裕でほぼ来ない

### Cursor 障害時
1. Anthropic API Key ON状態を活用 (OFFにしている場合は再ON)
2. Claude Code (claude.ai/code) または直接 Anthropic API で代替実装
3. Cursor 復旧後に通常運用に戻す

### gate_checker 系 OpenAI API 障害時
1. CostGuard が異常検知して停止 (装置3で Notion キューへ記録)
2. ジョブズが影響範囲を判定し LINE 通知
3. 代替: Anthropic Sonnet 4.6 で一時的にレビュー実施可 (品質ベンチ要)

---

## 4. プラン変更判断基準

### Pro $20 → Pro+ $60 (3倍枠) 移行判断
- **発動条件**: 2サイクル連続で Total 月末 70% 超
- **判断軸**: 月$40 増 vs 開発スピード(時間価値)
- **保留**: 当面 Pro で十分 (現状26%消費見込み)

### Pro+ $60 → Ultra (価格非開示) 移行判断
- "Ultra is recommended for agent power users" (公式)
- 当面検討不要

### Cursor 解約 (Free Plan化)
- 含有枠を完全に捨てるため経済合理性なし
- 検討対象外

---

## 5. 既知の前例・教訓

### 2026-06-01〜04: Anthropic 直接課金 累計約$220 スパイク
- **原因**: mail_pipeline FETCH_LIMIT 上限なし + 重複処理 ($50.88/日 インシデント含む)
- **対応済み**: CostGuard 実装 + Cursor完全移行(6/09) + ChatGPT Plus解約(6/12)
- **現状**: 6/05以降 Anthropic 直接課金は$1-2/日でほぼゼロ
- **教訓**: API直叩きスクリプトは必ず ledger.py 経由 (装置1〜4で再発防止強化中)

### 2026-06-16: 論点B(Cursor統合戦略) 確定
- 案A (Cursor Pro $20/月継続) で確定
- GPT-5.4 壁打ちで STOP級指摘 → 3点確認 → 全解消
- 「API課金ゼロ断定」を「現状ゼロ実測 + Cursor Pro内包仕様確認」に表現修正

---

## 6. Anthropic Key OFF判断 (任意, 影響ゼロ)

### OFFにする場合
- 現状 API used = 0% のため**機能影響ゼロ**
- メリット: Pro超過時の自動API課金リスクを排除 (On-Demand Disabled と二重防御)
- デメリット: Cursor障害時のBYOKフォールバックを失う

### ONのままにする場合
- 現状の挙動継続 (Cursor Pro 枠に吸収されてる仕様)
- Pro超過時のみ Anthropic API に流れる可能性 → On-Demand Disabled でも完全には防げない懸念

### 推奨
- **常時OFF** + 必要時のみ再ON (手順を memory 化)
- ただし押す押さないどちらでも当面実害なし

### 再ON手順 (障害/枠不足時)
1. Cursor → Settings → API Keys
2. Anthropic API Key 欄に既存キー貼り付け
3. ON切替
4. 必要に応じて On-Demand Spending も一時有効化

---

## 7. TODO (将来自動化)

| # | TODO | 優先度 | 担当 |
|---|---|---|---|
| 1 | Anthropic Admin Key 取得 → usage 自動取得 → LINE 通知 | Mid | ジョブズ提案 → 松野手動作成 |
| 2 | Cursor Usage API があれば連携 (公式提供未確認) | Low | ジョブズ調査 |
| 3 | 週次レポート: Cursor Pro + Anthropic + OpenAI 三系統コスト統合 | Mid | ledger.py 拡張 |
| 4 | 装置1〜4 実装 (Week1: 装置2+3 / Week2: 装置1 / Week3-4: 装置4) | High | 次チャットでCursor実装 |

---

## 変更履歴
| 日付 | 変更内容 |
|---|---|
| 2026-06-16 | v1初版。論点B確定(案A)に伴う運用ルール明文化。GPT-5.4壁打ち指摘の3点解消を反映。 |
"""

path = "C:/Users/ma_py/OneDrive/デスクトップ/ses_work/MODEL_ROUTING.md"
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK MODEL_ROUTING.md 作成完了")
print(f"   パス: {path}")
print(f"   サイズ: {len(content)} chars")
