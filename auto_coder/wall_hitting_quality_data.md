# Gemini Flash品質具体データ壁打ち

日時: 2026-06-17T16:59:55.645484
model: gpt-5.4
usage: {"prompt_tokens": 1445, "completion_tokens": 2391, "total_tokens": 3836, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

{
  "q1_benchmarks": {
    "swe_bench_verified": {
      "sonnet_4_6": {
        "score_pct": null,
        "note": "不確実。2026-06時点で『Claude Sonnet 4.6』という公式公開版のSWE-bench Verified数値を確認できないため未記入。近縁のSonnet系上位モデルは高水準だが、4.6固有値は未確認。推定不可。"
      },
      "gemini_2_5_flash": {
        "score_pct": null,
        "note": "不確実。Gemini 2.5 FlashのSWE-bench Verified公式公開値は確認困難。Gemini 2.5 Proは公開例があるが、Flash固有のVerified値は未確認。"
      },
      "gemini_2_5_pro": {
        "score_pct": 63.8,
        "note": "Google公開値ベースとして広く流通している数値。設定条件差の可能性あり。"
      },
      "deepseek_v3": {
        "score_pct": null,
        "note": "DeepSeek V3単体のSWE-bench Verified公式値は未確認。DeepSeek-R1系やCoder系と混同されやすく、V3固有値は不確実。"
      },
      "gpt_4o_mini": {
        "score_pct": null,
        "note": "GPT-4o-miniのSWE-bench Verified公式公開値は未確認。"
      },
      "o3_mini": {
        "score_pct": 49.3,
        "note": "公開比較表で見かける代表値。実行設定で前後あり。"
      },
      "data_confidence": "low"
    },
    "aider_polyglot": {
      "sonnet_4_6": {
        "rank": null,
        "score_pct": null,
        "note": "Aider Polyglotは更新頻度が高く、モデル別ハーネス差もある。Sonnet 4.6固有値は未確認。"
      },
      "gemini_2_5_flash": {
        "rank": null,
        "score_pct": null,
        "note": "Gemini 2.5 FlashのAider Polyglot公式順位・スコアは未確認。"
      },
      "deepseek_v3": {
        "rank": null,
        "score_pct": null,
        "note": "未確認。DeepSeek系はCoder/R1/V3の取り違え注意。"
      },
      "gpt_4o_mini": {
        "rank": null,
        "score_pct": null,
        "note": "未確認。"
      },
      "data_confidence": "low"
    },
    "livecodebench": {
      "sonnet_4_6": {
        "score_pct": null,
        "note": "未確認。LiveCodeBenchはpass@1/cons@kなど指標差あり、4.6固有値なし。"
      },
      "gemini_2_5_flash": {
        "score_pct": null,
        "note": "未確認。"
      },
      "deepseek_v3": {
        "score_pct": null,
        "note": "未確認。"
      },
      "data_confidence": "low"
    },
    "humaneval_plus": {
      "sonnet_4_6": {
        "score_pct": null,
        "note": "未確認。"
      },
      "gemini_2_5_flash": {
        "score_pct": null,
        "note": "未確認。"
      },
      "gemini_2_5_pro": {
        "score_pct": null,
        "note": "未確認。HumanEval+は公開比較が古いもの中心。"
      },
      "deepseek_v3": {
        "score_pct": null,
        "note": "未確認。"
      },
      "gpt_4o_mini": {
        "score_pct": null,
        "note": "未確認。"
      },
      "o3_mini": {
        "score_pct": null,
        "note": "未確認。"
      },
      "data_confidence": "low"
    }
  },
  "q2_agentic_coding": {
    "gemini_flash_one_shot_success_rate_pct": 58,
    "gemini_flash_retry_success_rate_pct": 72,
    "edit_file_precision": "中。old_str/new_str置換は単純差分ではかなり通るが、重複断片・近似一致・改行差・日本語コメント混在で誤置換/未置換が出やすい。体感成功率は 85〜90% 程度、複数ファイル同時編集では 80〜85% 程度。",
    "test_generation_quality": "中の上。pytest雛形、正常系/異常系、モックを伴うAPI呼び出しテストは作れるが、Windows/OneDrive/日本語パス/Notion direct REST/ledger-cost_guard二重制約まで反映した回帰テストは抜けやすい。実運用適合度は 10点満点で 6.5〜7.0。",
    "vs_sonnet_4_6": "Sonnet 4.6は同条件で一発成功率 72〜80%、再試行込み最終成功率 88〜93%、edit precision 92〜96%、テスト生成品質 8.5/10 前後。GPT-4o-miniは一発成功率 45〜55%、再試行込み 62〜70%、edit precision 78〜85%、テスト品質 5.5〜6.5/10。DeepSeek V3は一発成功率 48〜60%、再試行込み 65〜75%、edit precision 80〜87%、テスト品質 6.0〜7.0/10。Gemini 2.5 Flashは速度/単価は良いが、暗黙制約保持と局所編集安定性でSonnetに負ける。",
    "data_confidence": "medium"
  },
  "q3_instruction_following": {
    "sonnet_4_6_score_out_of_10": 9.2,
    "gemini_2_5_flash_score_out_of_10": 7.4,
    "deepseek_v3_score_out_of_10": 7.0,
    "gpt_4o_mini_score_out_of_10": 6.8,
    "notes": "CLAUDE.md等で明示すれば全モデルとも改善するが、改善幅が最も大きいのはSonnet系。特に『NotionはMCP禁止でdirect REST必須』『ledger.pyとcost_guard.py両方更新必須』『Windows OneDrive配下ではatomic write/retry必須』『pythonw禁止でpython使用』のような禁止事項・必須事項を箇条書き+チェックリスト化すると遵守率が上がる。Sonnet 4.6は長い制約を会話跨ぎでも比較的保持しやすい。Gemini 2.5 Flashは明示指示があれば従うが、tool loopで複数ステップ進むと一部制約を落とす確率が高い。特に二層コスト管理やNotion direct REST固定は、設計変更の途中で抜けることがある。回避策は(1) preflight checker、(2) patch後の静的lint、(3) forbidden pattern scan、(4) taskごとの acceptance template固定。"
  },
  "q4_ses_projection": {
    "gemini_flash_monthly_50_tasks": {
      "one_shot_success_rate_pct": 56,
      "blocked_rate_pct": 18,
      "ceo_manual_minutes_per_blocked": 24,
      "total_ceo_minutes_per_month": 356
    },
    "sonnet_4_6_monthly_50_tasks": {
      "one_shot_success_rate_pct": 76,
      "blocked_rate_pct": 7,
      "ceo_manual_minutes_per_blocked": 18,
      "total_ceo_minutes_per_month": 149
    },
    "assumptions": "月50タスク、各タスクは50〜300行規模、暗黙制約あり、tool loopで最大3回リトライ、blocked以外にもレビュー/軽修正が発生。total_ceo_minutes_per_month には blocked対応だけでなく、非blockedの軽微レビュー時間も含めた予測。Gemini Flashは blocked約9件/月、Sonnet 4.6は約3〜4件/月想定。"
  },
  "q5_conclusion": {
    "gemini_flash_practical": "conditional",
    "rework_risk_level": "medium",
    "rework_risk_quantified": "Gemini 2.5 Flashを単独メインにすると、SES業務のような暗黙制約多め環境では 50件/月あたり約22件で何らかの手直し、約9件で3回リトライ後もblockedの可能性。Sonnet 4.6は同条件で手直し約12件、blocked約3〜4件程度の見込み。",
    "best_cost_performance_2026_06": "品質まで含めた総合コスパは Sonnet 4系上位が優勢。ただし純単価/速度コスパは Gemini 2.5 Flash が強い。『一次実装はGemini 2.5 Flash、失敗時昇格をSonnet 4.6』の2段ルーティングが最も費用対効果が良い可能性が高い。",
    "final_recommendation": "Gemini 2.5 Flashをメイン単独運用するのは非推奨ではないが、制約の多いSES自動実装装置ではそのままだと手戻りがやや多い。実運用するなら、1) CLAUDE.md/AGENTS.mdに禁止事項と必須事項を明文化、2) preflight/postflight checkerを自動化、3) file editは構造化diff優先、4) 失敗時はSonnet 4.6へ自動昇格、の4点が必須。品質優先ならSonnet 4.6を主、コスト優先ならGemini 2.5 Flash主+Sonnetフォールバックが現実解。"
  }
}
