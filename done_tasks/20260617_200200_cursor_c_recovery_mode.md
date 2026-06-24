# Cursor作業指示 c: recovery_mode 正式実装(段階拡大の永続化)

最終更新: 2026-06-17 20:01 (ジョブズ作成)
GPT-5.4 round1/round2 壁打ち合意済み

## 背景

2026-06-17 緊急復旧時に、PROCESS_LIMIT を 50→10 / FETCH_LIMIT を 200→50 に手動で縮小した。
今後 backlog 状況と安定動作を見ながら 3 日かけて段階的に通常運用へ復帰する計画:

| Day | PROCESS_LIMIT | FETCH_LIMIT | 条件 |
|---|---|---|---|
| Day 0 (今夜) | 10 | 50 | 緊急復旧 |
| Day 1 (翌日) | 20 | 100 | Day 0 で 4連続OKなら昇格 |
| Day 2 | 30 | 150 | Day 1 で安定なら昇格 |
| Day 3 (通常) | 50 | 200 | Day 2 で安定なら通常運用復帰 |

この昇格を毎回手動でやると忘れる、再障害時の縮退も手動になる、という運用負債が大きい。
**段階拡大ロジックを永続化(コード化)する**のが本タスク。

ただし CEO の判断軸(法人化準備・TERRA依存脱却・安定性)から外れないよう、
**完全自動ではなく「条件を満たした場合だけ提案を出し、松野が最終確定する」モード**で実装する。

## 対象ファイル

- 新規作成: `mail_pipeline/recovery_mode.py`
- 新規作成: `mail_pipeline/recovery_state.json` (現在のフェーズと判定材料)
- 設定追加: `config/.env` に `RECOVERY_MODE=true` (デフォルト false)
- 統合先: `mail_pipeline/mail_pipeline.py`

## 作業内容

### Phase 1: 状態定義
recovery_state.json のスキーマ:
```json
{
  "current_phase": "day0_emergency",  // day0_emergency / day1_warmup / day2_warmup / day3_normal
  "phase_started_at": "2026-06-17T19:48:00+09:00",
  "process_limit": 10,
  "fetch_limit": 50,
  "consecutive_success_count": 0,
  "consecutive_failure_count": 0,
  "last_metrics_ts": "2026-06-17T19:53:00+09:00",
  "promotion_proposal_pending": false,
  "promotion_proposal_to": "day1_warmup",
  "promotion_proposal_at": null,
  "promotion_decided_by": null,
  "promotion_decided_at": null
}
```

### Phase 2: 昇格判定ロジック
`recovery_mode.py` が毎回 mail_pipeline 実行終了後に呼ばれる(metrics_recorder と統合):

```python
def evaluate_promotion(state, recent_metrics):
    """state を更新し、昇格提案が必要なら True を返す."""
    # 成功条件: exit_code=0 AND notion_errors=0 AND mails_new > 0
    success = (
        recent_metrics["exit_code"] == 0 and
        recent_metrics["notion_errors"] == 0 and
        recent_metrics["imap_errors"] == 0
    )
    if success:
        state["consecutive_success_count"] += 1
        state["consecutive_failure_count"] = 0
    else:
        state["consecutive_failure_count"] += 1
        state["consecutive_success_count"] = 0
    
    # 昇格条件: 現フェーズで4連続成功
    PROMOTION_THRESHOLD = 4
    if state["consecutive_success_count"] >= PROMOTION_THRESHOLD:
        next_phase = NEXT_PHASE.get(state["current_phase"])
        if next_phase and not state["promotion_proposal_pending"]:
            state["promotion_proposal_pending"] = True
            state["promotion_proposal_to"] = next_phase
            state["promotion_proposal_at"] = datetime.now().isoformat()
            return True
    
    # 縮退条件: 2連続失敗で1段階下げる提案
    DEMOTION_THRESHOLD = 2
    if state["consecutive_failure_count"] >= DEMOTION_THRESHOLD:
        prev_phase = PREV_PHASE.get(state["current_phase"])
        if prev_phase and not state["promotion_proposal_pending"]:
            state["promotion_proposal_pending"] = True
            state["promotion_proposal_to"] = prev_phase  # 実は demotion
            state["promotion_proposal_at"] = datetime.now().isoformat()
            return True
    
    return False
```

### Phase 3: LINE 提案フォーマット
昇格/縮退提案時にLINE通知:
```
[recovery_mode 昇格提案]
現状: day0_emergency (process_limit=10 / fetch_limit=50)
提案: day1_warmup (process_limit=20 / fetch_limit=100)
根拠: 直近4回連続成功(exit=0, notion_errors=0)
LINE返信:
  「昇格OK」→ 次回起動から新limit適用
  「却下」→ 提案保留、当面据え置き
  「明日まで」→ 提案を一時保留
```

### Phase 4: LINE Bridge 統合
- LINE Bridge側の line_bridge.py で「昇格OK」「却下」「明日まで」を解釈
- 「昇格OK」受信時に recovery_state.json を更新、新 limit を適用
- 「却下」: promotion_proposal_pending=false、phase維持
- 「明日まで」: 24時間後に再提案

### Phase 5: 縮退時の安全装置
- 2連続失敗で1段階下げ
- ただし day0_emergency より下には下げない(これ以下はメール基盤が完全停止)
- 縮退提案は **CEO 確認なしで即時実行**(障害時の即応性優先)
- ただし下げた事実は LINE 通知必須

### Phase 6: フェーズ手動上書き機能
緊急時にCEOがLINEで:
```
recovery_mode set day3_normal
recovery_mode set day0_emergency
```
を打つと、recovery_state.json が即更新される。

## 完了条件

- recovery_mode.py 実装、ユニットテスト6件以上
- recovery_state.json の初期値が day0_emergency / 10 / 50 で書き込まれる
- mail_pipeline.py と統合(metrics 後に evaluate_promotion を呼ぶ)
- LINE Bridge との連携テスト(昇格OK/却下/縮退/手動上書き 4パターン)
- Day1〜Day3 のphase遷移シミュレーション(unit testで)

## ゲート

- ゲート①: SPEC設計後 GPT-5.4 で `python gate_checker/gate_check.py --phase design --file mail_pipeline/SPEC_recovery_mode.md`
- ゲート②: 実装完了後 GPT-5.4 で `python gate_checker/gate_check.py --phase implementation --file mail_pipeline/recovery_mode.py`

## CEO確認必要事項(実装はしてよいが、有効化はCEO判断)

- `RECOVERY_MODE=true` への切替(本番反映)
- PROMOTION_THRESHOLD = 4 の妥当性
- 「昇格は提案・縮退は即時」というポリシーの妥当性

## 参照

- 引き継ぎ: 2026-06-17_メール基盤緊急復旧 (■未完了 #3, #4, #7c)
- ジョブズ行動憲法 #1 (実装はCursorに投げる)
- GPT-5.4 round2 (P6: PROCESS_LIMIT昇格判断はCEO確認寄り)
