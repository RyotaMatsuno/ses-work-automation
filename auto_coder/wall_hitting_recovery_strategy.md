# mail_pipeline復旧戦略 壁打ち

日時: 2026-06-17T17:53:11.406214
model: gpt-5.4
usage: {"prompt_tokens": 1322, "completion_tokens": 2253, "total_tokens": 3575, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

{
  "q1_a_safety": {
    "risk_level_50usd_recurrence": "low",
    "estimated_max_daily_cost_usd": 8.0,
    "reasoning": "A案を『6/4実績版へ巻き戻し』かつ『SPEC記載の安全装置が正常動作している』前提で評価すると、過去の$50/日級再発リスクは低いです。理由は、過去暴走の主因が FETCH_LIMIT=2000 と dedup破損による大量再処理であり、現状SPECでは FETCH_LIMIT=200・PROCESS_LIMIT=50・processed_ids上限・7日SINCE・call_claude先頭の日次$2チェック・Global Kill-Switchの日次$8停止が多層で効くためです。特に$50/日は、複数タスク連鎖や再課金継続が前提ですが、今回は mail_pipeline 単体復旧局面であり、Cloud Run含む全停止の上限があるため、同規模再発には複数防壁の同時破綻が必要です。ただし『安全』は $50/日を防ぐ意味では高い一方、Notion 500再発や backlog処理効率の問題までは保証しません。また、日次$2チェックが mail_pipeline の全AI呼び出し経路を本当に網羅しているか、Kill-Switchが警告のみでなく実停止まで自動で効くか、6/4版でも dedup が正常か、の3点が未確認なら残余リスクは残ります。",
    "guard_effectiveness": "対$50/日再発防止には強いです。一次防壁=$2日次AIスキップ、二次防壁=$8で全停止、三次防壁=FETCH/PROCESS上限、四次防壁=Cloud Run kill。仮に1メール単価見積がずれても、上位の金額制御で日次損失は原則$8以下に圧縮されます。したがって『A案フル稼働で即$50/日』は起きにくいですが、『$2〜$8の範囲で無駄打ちする』『Notion失敗で進捗しない』可能性はあります。なのでコスト面だけ見ればAはかなり安全、運用面を含めるとBの方が安全余裕があります。"
  },
  "q2_5day_strategy": {
    "default_8d_consumption_acceptable": "yes",
    "faster_alternatives": [
      {
        "option": "B+一時的にCron頻度を15分化しPROCESS_LIMIT=25",
        "throughput_per_day": 2400,
        "pros": "1回あたり負荷を下げつつ日次処理量は維持。Notion/APIスパイクを抑えやすい。",
        "cons": "Cron設定変更が必要。監視点が増える。"
      },
      {
        "option": "B+夜間のみPROCESS_LIMIT=20、日中10",
        "throughput_per_day": 720-960,
        "pros": "CEOの慎重運用に合う。初日観察向き。",
        "cons": "解消がさらに遅い。"
      },
      {
        "option": "段階的に10→20→30→50へ増やす",
        "throughput_per_day": "480→960→1440→2400",
        "pros": "実装軽微で十分安全。5%ロジック新規実装より簡単。",
        "cons": "完全消化まで数日余分にかかる。"
      },
      {
        "option": "AI不要メールを先にルールベースでスキップ/軽処理",
        "throughput_per_day": "実質増加",
        "pros": "コストを増やさず backlog解消速度を上げられる可能性。",
        "cons": "即日実装できるなら有効だが、判定ミスのリスクあり。"
      }
    ],
    "recommended_approach": "8.3日での自然消化は、コスト最優先・事故再発回避を重視するなら妥当です。むしろ20,000件 backlog がある状況で、処理速度を無理に上げるより『再発なく継続処理できること』が重要です。推奨は Bベースで、初日 PROCESS_LIMIT=10、問題なければ翌日20、翌々日50 に戻す簡易ランプアップです。もし日次処理量を落としたくないなら『15分Cron × 25件』の方が、50件を30分ごとにまとめて投げるよりシステム負荷が平準化されて安全です。"
  },
  "q3_5percent_interpretation": {
    "existing_guards_sufficient": "partial",
    "ceo_memory_likely_referring_to": "本番復旧や新機能有効化時に、処理対象量またはAIコール量を段階的に増やす運用原則を指している可能性が高いです。つまり『最初からフル流量を流さない』というリリース手順の記憶であり、単なる日次予算上限とは少し意味が違います。",
    "if_implement_5percent_design": "新規実装するなら、全20,000件の5%ではなく『通常期待日量または backlog対象量に対する処理上限』として実装するのが現実的です。例: recovery_mode=true 時に recovery_cap_per_day を持ち、Day1=120件、Day2=240件、Day3=480件、Day4=960件、Day5=1920件、以後2400件上限。各日、(1) Notion成功率>99%、(2) fatal error 0、(3) cost<$2または許容上限内、(4) duplicate率閾値以下、の条件を満たしたら翌日に倍率2x、満たさなければ据え置き/縮退。実装は state.json or Firestore/Notion config に current_stage, processed_today, last_promotion_at を保存し、Cronごとに残枠のみ処理。さらに manual override で stage固定可にする。",
    "recommendation": "既存ガードは『金額暴走抑止』としては十分ですが、『慎重な段階拡大運用』の代替としては不完全です。したがってCEO要望を満たすには、重い5%専用ロジックを今すぐ作るより、まずは運用で B案の 10→20→50 など簡易ランプアップを採用するのが最適です。恒久対策として後日『recovery_modeの段階上限』を入れるのは有益ですが、今回の復旧ブロッカーではありません。"
  },
  "q4_recommended_scenario": {
    "best": "B",
    "second_best": "A",
    "reasoning": "最適解はBです。理由は、Aと比較して復旧速度は少し落ちるものの、CEOの慎重姿勢・過去の暴走履歴・今回の原因が6/16修正起点であることを踏まえると、『6/4稼働実績版に戻したうえで流量だけ絞る』のが最もバランスが良いからです。Dは事業影響が大きすぎ、案件登録停止が続くため不適。Cは思想としては良いですが、いま障害中に新規ロジックを足すのは変更面積が増え、復旧時の不確実性を上げます。今回の本質は“安全な既知良品へ戻す”ことであり、“障害中に新機能実装する”ことではありません。",
    "specific_steps": [
      "1. mail_pipeline.py を 6/4稼働実績版(.bak_phase4)へ即時ロールバック",
      "2. 本番投入前に staging/ローカルで Notion query/create/update の疎通確認、1〜3通だけ手動試験",
      "3. call_claude の日次$2チェックが全経路で効くこと、Global Kill-Switch の実停止動作をコード/設定で再確認",
      "4. 初日は PROCESS_LIMIT=10、FETCH_LIMIT=50〜100程度に一時縮小して再開",
      "5. 2〜3実行枠連続で Notion 200系・重複異常なし・コスト正常なら翌日 PROCESS_LIMIT=20",
      "6. さらに半日〜1日安定なら PROCESS_LIMIT=50 に復帰",
      "7. backlog処理中はメトリクスを毎実行で記録: fetched, processed, created, updated, skipped, notion_500_count, AI_cost_usd",
      "8. backlog完了後に恒久対策として recovery_mode/段階上限ロジックを別PRで実装",
      "9. 6/16の119行追加差分は障害切り分けのため feature flag 下に隔離し、原因確定まで本線へ戻さない"
    ]
  },
  "q5_cost_estimate": {
    "day1_2400_emails_usd": 2.0,
    "total_recovery_20000_emails_usd": 16.7,
    "monthly_normal_operation_usd": 60.0,
    "worst_case_daily_usd": 8.0
  }
}
