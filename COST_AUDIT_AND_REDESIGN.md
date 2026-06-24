# 自動マッチング機構 コスト監査 & 再設計SPEC
作成: 2026-06-05 / 作成者: ジョブズ / 対象: SES自動化全システム
ステータス: 設計完了・Sonnet実装待ち

---

## 0. 結論（先に言う）

**「自動マッチングの仕組みはコスト的に問題ない」という前提は誤り。**
直近11日（5/25-6/4）の実API課金は **約$260（1日平均$23、ピーク$54/日）**。
matching_v3 configが想定する **「$6/日・$140/月」の約4〜5倍**。
このランレートが続けば **月$700〜$1,000ペース**。

さらに重大なのは、**「$15/日でタスクを止めるはずのcost_guard」が稼働していた期間に$37〜$54/日が発生していた** こと。
= コスト制御は実際には機能していなかった（事実として証明済み）。

原因は単一バグではなく**アーキテクチャ欠陥**：コスト制御がコンポーネントごとにバラバラで、
LLMを叩く経路が8系統あるのに、グローバルなキルスイッチが実質1系統しかカバーしていない。

---

## 1. 実コストの事実（cost_log.jsonl 90,596件を集計）

| 日付 | 合計 | コール数 | 内訳 |
|---|---|---|---|
| 05-27 | $37.81 | 16,034 | matching_v2 $28.3 / mail_pipeline $9.5 |
| 05-28 | $26.14 | 8,550 | matching_v2 $19.5 / mail_pipeline $6.7 |
| 05-29 | $44.62 | 10,553 | matching_v2 $40.8 / mail_pipeline $3.8 |
| 06-01 | $54.16 | 19,648 | mail_pipeline $37.7 / matching_v2 $16.5 |
| 06-02 | $50.88 | 17,621 | mail_pipeline $31.7 / matching_v2 $19.2 |
| 06-03 | $32.92 | 12,041 | mail_pipeline $26.2 / matching_v2 $6.7 |
| 06-04 | $13.75 | 6,137 | mail_pipeline $13.75（v2は停止） |

- 累計（ログに出ている分のみ）: matching_v2 $131.07 / mail_pipeline $129.25 / **合計$260.3**
- モデル別: Haiku $259.60 / Sonnet $0.72（Sonnetはほぼ無視できる量）
- matching_v2は6/3で停止（git 430897cでの無効化と整合）。**現在の主犯はmail_pipeline。**

---

## 2. LLMコスト発生経路の全数洗い出し（8系統）

| # | 経路 | 実行頻度 | モデル | cost_logに記録? | キルスイッチ対象? | 独自上限? |
|---|---|---|---|---|---|---|
| A | mail_pipeline 同期呼び出し（extract_affiliation / ai_matching[max2000] / double_check） | 30分毎 | Haiku | ✅ | ✅ | $2/日（同期のみ） |
| B | mail_pipeline Batch分類（classify_email_v2/send_batch） | 30分毎 | Haiku | **❌ 未記録** | △（タスク停止で止まる） | **❌** |
| C | matching_v2 | 停止済（旧:手動/テスト多用） | Haiku | ✅ | △（既にDisabled=no-op） | ? |
| D | matching_v3 本番（SES_MatchingV3） | 毎日8:00 | Haiku | **❌ 0件記録** | **❌ 対象外** | $6/日（**盲目=後述**） |
| E | matching_v3 dry-run/phase0テスト | 手動・高頻度 | Haiku | **❌ phase0_cost_log.jsonl別管理** | **❌** | 別ガード・簿外 |
| F | Cloud Run webhook_server | 常時・LINE着信毎 | Haiku(max2000) | **❌ リモートで記録不可** | **❌ Winタスクでない** | **❌** |
| G | Cloud Run skill_extractor | LINEスキルシート毎 | Haiku(max2000) | **❌** | **❌** | **❌** |
| H | outlook_to_notion | 1日3回(9/13/18時) | **Sonnet** | **❌ 未記録** | **❌** | **❌** |
| - | attachment_importer(ai_extractor) | jobz_importer 毎日8:00 | Haiku(max2000) | **❌ 未記録** | **❌** | **❌** |

**→ 8系統中、グローバルキルスイッチが実際にカバーしているのは A のみ（Cは無効化済タスクでno-op）。**
**残り B,D,E,F,G,H + importer は「記録されない／止められない／上限なし」。**

---

## 3. 個別の重大欠陥

### 3-1. グローバルcost_guard（SES_CostGuard）が主犯を止められない【致命的】
- `disable_tasks()` が止めるのは `SES_MailPipeline` と `SES_MatchingAndNotify` の2つだけ。
- `SES_MatchingAndNotify` は既にDisabled → **停止しても効果ゼロ**。
- **現在アクティブな `SES_MatchingV3` / `jobz_importer` / `SES_Outlook×3` / Cloud Run は停止対象外。**
- 実績：$37〜$54/日が発生した日に止まっていない。閾値$15/日が**機能していない**ことが証明済み。

### 3-2. matching_v3の$6/日上限が「盲目」【致命的】
- `CostGuard.can_call()` は `script=="matching_v3"` のエントリだけを集計して日次コストを判定。
- しかし matching_v3 の実コストは **cost_log.jsonlに0件**（記録経路が壊れている）。
- → 日次集計が常に$0 → **can_callは永遠にTrue → 上限が一度も発動しない。**
- 実績：6/3に400回、6/4に730回の実API成功（ログ確認済）。**計1,130回が事実上未追跡。**

### 3-3. mail_pipelineの構造的浪費【高】
- **「intake専用」のはずがmain()内でフルパイプラインを毎回実行**：
  projectメール毎に `extract_affiliation` + `ai_matching(max_tokens=2000)` を同期呼び出し（+draft生成）。
  → 30分毎×全projectメールに対し高コストなマッチング/起案を実行（設計意図と逆行）。
- **dedupキーが不安定**：Message-ID無しメールは `no-id-{IMAP連番}-{user}` を採番。
  IMAP連番はセッション毎に変わる → **該当メールは毎回「新規」扱い→30分毎に再分類・再課金。**
- **実ログで「新規処理対象」が毎回2,000件超**（516→2,111→2,171→2,171→2,156）。
  dedup/バックログが崩壊しており、PROCESS_LIMIT=50で延々と処理し続ける状態。
- **Batch分類のコストがlog_costされていない**（send_batchにlog_cost無し）。
  → 実支出は$129より大きい。かつ$2/日ゲート（同期パスのみ）にもカウントされない。

### 3-4. matching_v3のコスト劣化フォールバックが壊れている【中】
- `cost_guard.get_model()` は$120/月超で `gemini-2.0-flash` を返す設計。
- しかし `structurer._call_anthropic()` は**常にanthropic.Anthropic()でmodel=を渡す**。
- → model="gemini-2.0-flash" をAnthropic APIに渡す → **404エラーで全件失敗（劣化せず停止）。**
- 救い：エラーは課金されない（金銭的にはfail-safe）。が$120超でマッチング全停止する設計欠陥。

### 3-5. dry-run/phase0テストが簿外で課金【中】
- dry-runは `phase0_cost_log.jsonl`（17KB）に記録 → グローバルcost_guardもusage_trackerも読まない。
- matching_v3のチューニング（壁打ち×3、Phase0-3）の度にfixture全件を実API構造化 → 簿外課金。
- 巨大ログ（match_results_bak.jsonl **89MB**, match_results.jsonl 20MB）はこのテスト由来。

### 3-6. コスト確認が13MBファイルの全読み【低・運用劣化】
- `get_today_cost_usd()` / matching_v3 `CostGuard._iter_entries()` は呼び出し毎にcost_log.jsonl(13MB)を全行読込。
- 1案件処理あたり3〜4回フル読込。ファイル増大に比例して遅くなる → タイムアウト誘発リスク。

---

## 4. マッチング判定ロジックの品質欠陥（matcher.judge）

コストだけでなく「判定の正しさ」も検証。判断マニュアルv3との乖離：

### 4-1. 単価バンドが緩すぎる → 逆ザヤMATCH【致命的・金銭直結】
- 現状：`eng_price > case_max + 15` でのみNG。
- 判断マニュアル：調整は最大5万、粗利最低5万、5万超乖離は提案しない。
- → **案件単価+15万までMATCH** = エンジニア単価が案件より高い「粗利マイナス」案件をMATCH判定。
  notifierが「推定粗利: 約{負数}万円」を松野/岡本に通知しうる。
- **修正：MATCH条件を `case_max - eng_price >= 5`（粗利5万床）に。NGは `eng_price > case_max - 5` 側で。**

### 4-2. 未知スキルを黙って無視【高】
- `normalizer.normalize(skill)` がNone（alias辞書に無い）の必須スキルは**充足扱いでスキップ**。
- skill_aliases.json(3.5KB)は小さく、実スキルの多くが未登録 → **必須不足でもMATCH。**
- → MATCH/REVIEW過多 → 通知増・起案LLMコール増（コストも押し上げる）。
- **修正：未知必須スキルは「要確認(REVIEW)」要因に。黙殺しない。**

### 4-3. 絶対除外ルール未実装【高・コンプラ】
- 外国籍/地方/短期連続/ブランク/既往歴 の絶対除外を judge は一切チェックしない。
- get_active_engineers も「提案対象フラグ」でフィルタしていない。→ 除外対象がMATCHしうる。
- **修正：get_active_engineersのfilterに `提案対象フラグ=true` を追加 + judge冒頭で除外属性チェック。**

### 4-4. 並行スコア超過がNGでなくREVIEW止まり【中】
- 判断マニュアル：合計5.0以上→提案NG。現状はREVIEW理由に追加するのみ。
- **修正：p_score>=5.0 はNG（または明示的に提案除外）に。**

---

## 5. LINE通知上限という第2の「コスト」リスク

- LINE Messaging APIフリープラン=月200通。memory上「定期的に上限到達」。
- matching_v3 Notifierは `PUSH_LIMIT_PER_DAY=8`（自分のぶんだけ）。
- だが200/月は **root cost_guardアラート / Cloud Run通知 / notify_line(週次+マッチング) / outreach と共有**。
- = コストと**全く同じ構造欠陥**（コンポーネント毎の上限・グローバル計数なし）。
- **修正：LINE送信も後述の共有レジャーで月次グローバル計数。閾値超でpushをqueue/抑制。**

---

## 6. 再設計（Sonnet実装対象）

### 設計原則
**「全てのLLM呼び出しとLINE送信は、単一の共有ゲートを必ず通る」** に作り替える。
バラバラの個別ガードを廃し、Single Source of Truthのレジャー＋全消費者を止められるキルスイッチにする。

### 6-1. 共有コストレジャー `ses_work/common/ledger.py`【最優先】
全コンポーネント（ローカル＆Cloud Run）が必ず呼ぶ2関数：
- `can_spend(est_in, est_out, script) -> bool` … グローバル日次・月次上限で判定
- `record(in_tokens, out_tokens, model, script)` … 課金記録（全経路必須）

実装方針：
- **増分状態ファイル** `cost_state.json`（当日・当月の累計を保持、呼出毎に+=のみ）を採用。
  13MB全読みを廃止。cost_log.jsonlは追記専用の監査ログとして残す（日次でローテート）。
- グローバル上限（要松野決裁・後述）：例 日次$8 / 月次$140（degrade $110）。
- モデル別正確レート表を内蔵（Haiku/Sonnet/Geminiを実価格で。現状$1/$5固定は要検証）。
- Cloud Run対応：Cloud RunはローカルJSONLを書けないため、**record()を「Notionコスト管理DBへAPI記録」モードで動作**させ、
  ローカルguardは(ローカル状態 + 当日Notion集計)を合算してグローバル判定。
  （MVPはCloud Run側に「インスタンス内日次カウンタ＋ハード上限」を入れ、並行してNotion記録で全体可視化）

### 6-2. グローバルキルスイッチ刷新（root cost_guard.py 全面改修）
- 監視対象をレジャーの**グローバル合計**に変更（script限定をやめる）。
- `disable_tasks()` の対象を**全アクティブ消費者**に：
  `SES_MailPipeline, SES_MatchingV3, jobz_importer, SES_Outlook_9h/13h/18h`。
- Cloud Runのキル：`gcloud run services update line-webhook --update-env-vars LLM_KILL=1`
  （webhook側はLLM_KILL=1ならHaiku呼び出しをスキップしてルール処理のみにフォールバック）。
- 段階制御：日次softlimit(例$6)で警告 → hardlimit(例$8)で全停止＋LINE。月次$140で停止。
- 実行頻度を5分毎に（現状の取りこぼし防止）。

### 6-3. mail_pipeline 再構築【高】
1. **intakeとmatchingを分離**：mail_pipeline.main()から `ai_matching`/`extract_affiliation(LLM)`/draft生成を撤去。
   intakeは「分類→Notion登録」のみ。マッチングはmatching_v3に一本化（重複実装の解消）。
2. **dedupキーを安定化**：Message-ID優先。無い場合は `sha1(from+subject+date+body[:200])`。IMAP連番は使わない。
3. **Batch分類をレジャー経由に**：send_batchの結果usageをrecord()。事前にcan_spend()でゲート。
4. **頻度見直し**：30分→60分（案件タイマーは2-6h、60分で十分。fetch/分類コスト半減）。
5. **prompt caching**：classify_system等の固定プレフィックスにcache_control付与（入力トークン大幅減）。

### 6-4. matching_v3 修正【高】
1. **record()を共有レジャーに接続**（盲目の$6上限を実効化）。3-2を解消。
2. **degradeパス修正**：Geminiを使うなら本物のGeminiクライアントを実装。
   使わないなら$120でmodel切替せず「停止のみ」に簡素化（誤ったmodel id送出を除去）。
3. **dry-run/phase0は実APIを叩かない**：録画済みfixture（構造化結果キャッシュ）で評価。
   実API評価は小サンプル(5-10件)のsmokeのみ。簿外課金を根絶。
4. **巨大ログのローテート**：match_results.jsonl/bak、phase0_*をアーカイブ＆圧縮。
5. judge品質修正（§4-1〜4-4を実装）。get_active_engineersに提案対象フラグfilter追加。

### 6-5. その他経路をレジャー配下に
- attachment_importer(ai_extractor)・outlook_to_notion・Cloud Run(webhook/skill_extractor)：
  全てcan_spend()/record()を通す。importerとoutlookにも日次上限。
- **outlookのSonnet→Haiku検討**：テキスト分類用途ならHaikuで5〜10倍安い（画像処理が無ければ即切替）。

### 6-6. 重複の解消（アーキ整理）
- マッチング実装が4箇所（mail_pipeline.ai_matching / matching_v2 / matching_v3 / Cloud Run matching_logic）。
- **matching_v3を唯一の正とし、他は段階的に撤去**。判定の一貫性とコスト管理点の一元化。

---

## 7. 段階実装プラン（3点セットはフェーズ毎に作成）

- **Phase 1（即時・止血／半日）**：root cost_guardの停止対象を全アクティブ消費者へ拡張＋5分毎化。
  これだけで「青天井で課金が積み上がる」最悪を即封じる。コード変更小・リスク低。
- **Phase 2（共有レジャー／1-2日）**：common/ledger.py新設。mail_pipeline・matching_v3・importer・outlookを接続。
  Cloud RunはNotion記録モード。グローバル上限を実効化。
- **Phase 3（mail_pipeline再構築／1-2日）**：intake/matching分離・dedup安定化・Batch記録・60分化・caching。
- **Phase 4（matching_v3品質／1日）**：judge §4修正・degrade修正・dry-run簿外根絶・ログローテート。
- 各PhaseはCLAUDE.md→SPEC.md→TASKS.md作成後、Codexで実装（ジョブズは設計・レビュー・Notion記録）。

---

## 8. 松野の決裁が必要な事項（これだけ決めれば自走で実装に入れる）

1. **グローバル上限の数値**：日次ソフト$? / 日次ハード$? / 月次$?（推奨：$6 / $8 / $140）。
2. **mail_pipeline頻度**：30分維持か60分化か（推奨：60分。コスト半減・実害なし）。
3. **mail_pipelineのintake/matching分離**：matching_v3一本化に同意するか（推奨：同意）。
4. **degradeポリシー**：$120超でGemini劣化運用 or 単純停止か（推奨：当面は単純停止＝実装が堅い）。
5. **outlook**：Sonnet→Haiku切替可否（用途が画像か要確認。テキストならHaiku推奨）。
6. **Cloud Runコスト可視化**：Notion記録モードで進めてよいか（推奨：可）。

決裁後、Phase1から順にCLAUDE/SPEC/TASKSを作成しSonnetで実装します。
