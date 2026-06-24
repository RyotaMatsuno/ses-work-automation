# auto_coderコスト問題の壁打ち

日時: 2026-06-17T16:47:16.767944
model: gpt-5.4
usage: {"prompt_tokens": 1069, "completion_tokens": 3249, "total_tokens": 4318, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

{
  "q1_claude_code_workaround": {
    "feasibility": "low",
    "methods": [
      {
        "name": "stdin自動応答(subprocess.Popen)で対話承認を流し込む",
        "steps": "Pythonでclaude code CLIをPopen起動し、stdout/stderrを監視して permission prompt / approve prompt を検知したら 'y\\n' や Enter をstdinへ送る。実装例: p = subprocess.Popen(['claude','code'], stdin=PIPE, stdout=PIPE, stderr=STDOUT, text=True); 逐次readし、'Allow edit' や 'Approve' などの文言に応じて p.stdin.write('y\\n'); p.stdin.flush()。必要なら初回にタスク指示文も投入する。",
        "risk": "CLI文言変更で即死しやすい。TTY必須ならPIPEでは動かない。フル自動運用では承認ダイアログの種類追加に追従が必要。安全性も低い。2026-06時点で『確実な公式解』とは言えない。"
      },
      {
        "name": "expect/pty/winptyで疑似TTY対話を再現",
        "steps": "Linux/macOSなら pexpect、Windowsなら pywinpty / winpty / ConPTY 経由で対話端末として起動し、プロンプトパターンをexpectして 'a' / 'y' / Enter を返す。例: pexpect.spawn('claude code', encoding='utf-8'); child.expect(['Approve','Allow write','Continue']); child.sendline('y')。タスク本文は起動後に貼り付けるか、ファイル読み込み指示を送る。",
        "risk": "Popenより成功率は高いが、CLI側のフルスクリーンUI/TUI実装次第で壊れる。Windows運用では特に不安定。5並列のCron運用と相性が悪い。ログ取得・タイムアウト処理も面倒。"
      },
      {
        "name": "環境変数/hidden flag探索",
        "steps": "claude code --help, claude --help, strings, envダンプ、リリースノート、GitHub issues、Discord等を調査し、 non-interactive / auto-approve / permissions=accept-all 相当の公開フラグがないか確認する。候補として CLAUDE_AUTO_APPROVE, CLAUDE_NON_INTERACTIVE, CI=1 などを試す。",
        "risk": "2026-06時点で一般公開・安定した『Edit/Writeを常時自動承認する公式環境変数』は確認困難。隠しフラグに依存すると次回更新で消える。運用基盤に据えるべきではない。"
      },
      {
        "name": "2.1.143以前へのダウングレード固定",
        "steps": "npm/pip/homebrew等の導入経路に応じて旧版を固定インストールし、アップデート抑止する。例: npm系なら package version pin、brewなら旧formula切替、バイナリ保管してPATH固定。task_auto_runner側で version check を入れて逸脱時にblockedへ送る。",
        "risk": "旧版で本当に動く保証がない。認証フローやサーバ側仕様変更で旧版が止まる可能性がある。セキュリティ/サポート面でも不安。短命な回避策。"
      },
      {
        "name": "CLIを捨ててAnthropic API SDK直叩きの自前tool loopへ移行",
        "steps": "Claude Code CLIの代わりにAnthropic APIのMessages/Responses系と自前ツール実行器を使い、Read/Edit/Write/Bash/Git toolsをローカル実装する。pending_tasks/の指示書を読み、repo context収集→LLM計画→差分生成→apply patch→テスト→コミット案まで自動化する。",
        "risk": "追加API課金が出る。初期実装に2〜5日程度必要。ただしCLIの挙動変化に振り回されず、最も再現性が高い。"
      }
    ],
    "recommended": "本命は『CLI回避』です。Claude Code CLI 2.1.144で完全自動承認を安定運用する現実性は低いです。短期の検証順は 1) pty/expectで疑似TTY承認を試す、2) 旧版固定を試す、3) ダメなら即CLIを捨てて安価APIベースの自前auto_coderへ移行、です。CEO要件(月$10理想)を満たすにはAnthropic API直叩きよりGemini Flash系かDeepSeek系での自前tool loopの方が適します。"
  },
  "q2_max_plan": {
    "api_credit_included": "no",
    "automation_path": "2026-06時点では、Anthropic Claude Maxプランは主にClaudeアプリ/Claude Code利用枠側の上位サブスクであり、通常のAnthropic API課金枠を包括するものではない扱いです。したがってMax契約だけで『APIキーを大量無料利用して自前自動化』する前提は置けません。Claude Code CLIにMaxの認証資格情報を流用して完全無人実行する公式・安定な手段も限定的で、少なくともサーバ常駐バッチのための“API代替”とは見なさない方が安全です。",
    "discount_for_max_users": "2026-06時点で、Max加入者向けに一般Anthropic API usageへ恒常的な大幅割引や無料クレジット付与が標準特典として明示されている前提ではないです。仮に一時的キャンペーンや企業向け優遇があっても、SES自動化装置の恒久設計の前提にすべきではありません。",
    "notes": "要点は『Max = API prepaid枠ではない』です。Cursor ProやClaude Maxは“人間が使う対話/IDE体験”のコスパは高いですが、pending_tasks/をcronで完全無人処理する基盤コストには直接変換しにくいです。自動化したいならAPI課金型かローカルモデル型へ設計変更が必要です。"
  },
  "q3_alternatives": [
    {
      "approach": "Gemini 2.5 Flash / Flash-Lite + 自前tool loop(auto_coder lite)",
      "monthly_cost_usd": 5,
      "code_quality_vs_sonnet": "lower",
      "implementation_effort_days": 2,
      "task_runner_compat": "yes",
      "notes": "最有力。Google AI Studio / Gemini APIは低単価で、編集・リファクタ・テスト修正の自動化には十分実用。設計: task_auto_runnerがpending_tasks/を拾う→repo要約→対象ファイル抽出→LLMにpatch生成→apply→pytest/npm test→再試行。長文推論や大規模設計はSonnet未満だが、SESの小〜中粒度実装なら費用対効果が高い。月間数百タスクでも$10前後に収まりやすい。Flash-Liteならさらに安いが品質は一段落ちる。"
    },
    {
      "approach": "DeepSeek V3/R1 API + Aiderまたは自前patch loop",
      "monthly_cost_usd": 3,
      "code_quality_vs_sonnet": "lower",
      "implementation_effort_days": 2,
      "task_runner_compat": "yes",
      "notes": "コスト最安クラス。V3はコード生成コスパが高く、R1は考える系だが遅くなりがち。実装はAiderを非対話モードで叩くか、自前で unified diff を返させる。日本語仕様理解や複雑な既存コード改修ではSonnetよりムラがあるため、テスト必須。CI的に『1回目V3、失敗時のみ高品質モデルへフォールバック』の前段モデルに非常に向く。"
    },
    {
      "approach": "GPT-4o-mini / o3-mini + 自前tool loop",
      "monthly_cost_usd": 8,
      "code_quality_vs_sonnet": "lower",
      "implementation_effort_days": 2,
      "task_runner_compat": "yes",
      "notes": "安価で安定。4o-miniは高速・低単価、o3-miniは推論寄り。既存コードの安全な編集、JSON厳格出力、関数呼び出し制御がやりやすい。コード品質はSonnetに少し劣るが、失敗時の再試行制御やschema出力が組みやすい。月$10以下を狙うならコンテキストを絞り、対象ファイル選定を別工程にすること。"
    },
    {
      "approach": "Aider(OSS) + 安いAPI(DeepSeek or Gemini Flash)",
      "monthly_cost_usd": 4,
      "code_quality_vs_sonnet": "lower",
      "implementation_effort_days": 1,
      "task_runner_compat": "partial",
      "notes": "最短導入。Aiderはgit差分中心の編集が得意で、自動コミットや複数ファイル編集に強い。難点は本来対話UX寄りなので、完全無人化には --message 相当の一発実行、対象ファイル列挙、終了コード・ログ解析のラッパーが必要。task_auto_runnerから呼ぶ統合は可能だが、AiderのCLI仕様変更への追従コストは少しある。"
    },
    {
      "approach": "OpenHands / Continue / Cline をローカルヘッドレス化してAPIはGemini/DeepSeek",
      "monthly_cost_usd": 10,
      "code_quality_vs_sonnet": "lower",
      "implementation_effort_days": 4,
      "task_runner_compat": "partial",
      "notes": "エージェント系OSSを使う案。複数ステップ作業・ファイル探索・コマンド実行が得意だが、ヘッドレス常駐化やWindows運用はやや重い。OpenHandsは自律性はあるがランタイム管理が増える。SESの『指示書を置くだけ』には合う一方、保守コストは自前tool loopより高くなりがち。"
    },
    {
      "approach": "ローカルLLM(Ollama + Qwen2.5-Coder 32B / DeepSeek-Coder系)で完全オフライン",
      "monthly_cost_usd": 0,
      "code_quality_vs_sonnet": "lower",
      "implementation_effort_days": 3,
      "task_runner_compat": "yes",
      "notes": "追加API費ゼロ。ただしWindowsで実用速度を出すにはVRAM 24GB級が欲しい。CPU実行は遅く、5並列は現実的でない。小規模修正・定型コードなら可能だが、既存巨大repoやテスト修正の成功率は低め。既存ハードに十分なGPUがないなら非推奨。"
    },
    {
      "approach": "ハイブリッド: 1st passをDeepSeek/Gemini、失敗時のみCursor手動 or Claude Max手動確認",
      "monthly_cost_usd": 2,
      "code_quality_vs_sonnet": "comparable",
      "implementation_effort_days": 2,
      "task_runner_compat": "yes",
      "notes": "完全無人ではないがCEOの作業を“1日5分”から“週数分”まで減らせる。大半の簡単タスクは安価モデルが自動処理、失敗タスクだけblocked_reviewへ回してCursorで人間最終仕上げ。総コスト最小・品質最大化の現実解。"
    }
  ],
  "ceo_recommendation": {
    "if_target_under_10usd": "Gemini 2.5 FlashまたはDeepSeek V3を使った『自前tool loop方式』を推奨。構成は task_auto_runner → repo context収集 → LLMでdiff生成 → apply patch → テスト → 成功ならdone、失敗なら最大3回再試行 → blocked。簡易版なら2日で入る。Anthropic CLI回避が前提。",
    "if_allow_up_to_30usd": "メインをGemini Flash or GPT-4o-mini、難タスクのみSonnet APIまたは人手フォールバックの二段構成を推奨。具体的には cheap modelで80〜90%自動処理し、失敗時のみ高品質モデルを使う。これで月$10〜$30内に収めつつ品質をかなり上げられる。",
    "reasoning": "現状ボトルネックはモデル品質ではなく『Claude Code CLIが完全無人前提で安定しない』点です。Cursor Pro/Claude Maxは人間向けUXとしては非常にコスパが良い一方、cron駆動の無人実装エンジンとしては使いにくい。したがって、最小コストでCEO要望を満たすには、CLI依存を捨ててAPIまたはローカルモデルでヘッドレス化するのが正攻法です。費用対効果では Gemini Flash系 > DeepSeek系 > GPT-4o-mini系 の順で有力、品質重視なら GPT-4o-mini か cheap+fallback のハイブリッドが安定です。"
  }
}
