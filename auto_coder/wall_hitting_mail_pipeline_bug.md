# mail_pipeline dedup破損 壁打ち

日時: 2026-06-17T17:11:21.600835
model: gpt-5.4
usage: {"prompt_tokens": 1100, "completion_tokens": 3099, "total_tokens": 4199, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

{
  "q1_duplicate_handling": {
    "recommended": "削除や物理マージはせず、重複2件とも即時にステータスを「終了」に変更し、可能なら「重複/誤取込」などの理由フラグを付与したうえでアーカイブ対象にする。既存の5/27登録・6/5終了済み正本レコードへリレーションまたは備考で『duplicate of <record_id>』を残すのが最善。",
    "reasoning": "ベストプラクティスは『監査証跡を残しつつ、業務上の有効対象から即除外』です。今回は既にmatching_v3が走り、さらに営業が意向確認メールを送った可能性もあるため、後から“なかったこと”にする削除は不向きです。Notion created_timeや自動化実行時刻が原因調査の重要証跡になるため、物理削除は避けるべきです。単純に「募集中」のまま残すのも誤通知再発リスクが高いです。『終了』化で業務フローを止め、補助的にアーカイブや原因ラベル付けで運用ノイズを下げるのが安全です。過去終了済みレコードとの完全マージは、Notion上で履歴・通知・参照IDが混ざりやすく、今回のような障害調査ではかえって不利です。正本は既存の5/27レコード、6/14作成分は誤取込の従属記録として扱うのが妥当です。",
    "pre_check_before_action": "実施前に 1) matching_v3通知先1名の所属/営業担当に実際に対外送信があったか確認、2) 6/14重複2件のpage_id・created_time・メールMessage-ID・本文ハッシュを保全、3) 既存5/27正本レコード2件との対応関係を確認、4) 再通知ジョブや募集中案件集計の参照条件に『終了』が確実に除外されることを確認。その後、重複2件を『終了』+『誤取込』タグ化し、コメント欄にインシデント番号・原因調査中・正本レコードIDを追記する。もし対外連絡済みなら、営業向けに『当該案件は鮮度切れの誤再取込』テンプレを別途出す。"
  },
  "q2_pollution_scan": {
    "query_design": "一次抽出は Notion案件DB に対して created_time の日付レンジで 2026-06-14 UTC 全件を取得する。Notion API filter例は created_time on_or_after=2026-06-14T00:00:00Z AND before=2026-06-15T00:00:00Z。取得後、案件詳細フィールド(rich_text)や保存済みメールヘッダ文字列から優先順で Message-ID, Date, From, Subject を抽出する。Date抽出後、JST基準の受信日へ正規化し、Notion created_timeとの差分営業日を計算。4営業日超を汚染候補とする。さらに同一Message-IDまたは本文ハッシュで既存レコードを横断照合し、過去に既登録・終了済み案件が存在するものは高優先度汚染としてフラグ付けする。",
    "thresholds": "基本閾値は『営業日差 > 4』。補助閾値として『暦日差 > 7』なら強い候補、『暦日差 > 20』ならほぼ確定汚染として扱える。今回のような週末・祝日影響を避けるため、正式判定は営業日で行う。created_timeとメールDateの時差が0-2日程度は、メールサーバ遅延・手動転送・タイムゾーン差で起こりうるため除外寄りに扱う。",
    "false_positive_filter": "誤検出を減らすには以下を除外/別扱いにする。1) 転送メール(Fwd:, FW:)や引用転記案件: 元Dateが古くても新規案件化の可能性あり。2) 再送案件: 件名が同一でも本文内に『再送』『最新』『条件変更』がある場合は自動確定しない。 3) 手動登録・手動修正ページ: created_byや更新履歴でbot以外なら別扱い。4) メールDate欠損/壊れ: Receivedヘッダや本文内日時を代替使用。5) 同一取引先が古いスレッドへ返信して新条件を送るケース: Message-IDではなく References/In-Reply-To が古いだけの可能性があるため、本文差分や案件条件更新語を確認する。最終的に『古いDate』『同一本文またはMessage-ID既存あり』『終了済み正本あり』の3点一致なら自動汚染でよい。",
    "implementation_notes": "Pythonでは notion-client で pagination を回しつつ抽出。rich_textはプレーンテキストへ連結してから email.utils.parsedate_to_datetime でDate解析。Message-IDやDateが本文保存されていない場合に備え、mail_pipelineが原文EMLやヘッダJSONを保持している保存先も引く。営業日計算は pandas.tseries.offsets.CustomBusinessDay か japan-holidays ライブラリ利用。本文ハッシュは正規化後に sha256 を推奨。正規化は改行統一、引用符除去、署名・フッタ除去、全角空白整理。出力はCSVで page_id, created_time, parsed_mail_date, business_day_diff, message_id, from, subject, duplicate_of, suspicion_level を出すとレビューしやすい。クエリはcreated_time日単位で絞った後にPython側判定が現実的で、Notion単体ではrich_text内Date抽出条件を表現しづらい。"
  },
  "q3_created_time_strategy": {
    "recommended_letter": "combo",
    "design": "推奨は A+C の組み合わせ。A: Notionに『受信日』date型、可能なら『Message-ID』『メール受信日時(raw UTC/JST)』『取込日時』も追加。C: LINE通知や鮮度判定、matchingの有効期限判定は created_time ではなく『受信日』を参照する。created_time はあくまでNotionページ作成時刻＝監査/ETL証跡として残す。Bの案件名先頭日付埋め込みは視認性向上には役立つが、データ品質の主軸にしてはいけない。件名や案件名は人間向け表示であって、機械判定キーに不向き。理想設計は『受信日時(業務意味)』と『取込日時(システム意味)』の分離。",
    "migration_plan": "1) スキーマ追加: 受信日(date), message_id(rich_text/title不可ならtext), mail_from, mail_subject_normalized, source_mail_hash, ingestion_time(optional) を追加。2) mail_pipeline改修: IMAP取得時にRFC822 DateをUTCへ正規化し受信日に保存、Message-IDも保存。Date欠損時のみ INTERNALDATE か Received最終段をフォールバック。3) 通知改修: LINE文面の『3日前』計算元を受信日に変更。4) 鮮度判定改修: 4営業日ルールを受信日ベースへ統一。5) 既存データバックフィル: 案件詳細や保存メールからDate/Message-IDを抽出し受信日へ埋める。抽出不能は created_time を暫定値にし quality_flag=estimated を付ける。6) 監視追加: created_timeと受信日の差が5営業日超ならアラート。7) 運用移行: 一定期間は created_time と受信日を並列表示し、下流ジョブが全て受信日参照へ切り替わった後、created_time依存ロジックを廃止。"
  },
  "q4_dedup_root_cause": {
    "top3_hypotheses": [
      {
        "hypothesis": "processed_ids などの永続dedupストア破損・ローテーション漏れ・再初期化により、5/12メールが未処理扱いで再投入された。",
        "evidence_to_check": "6/14前後のdedupストア件数推移、保存先の再作成/truncate、デプロイやコンテナ再作成履歴、キー形式変更、Message-ID単位の存在確認、5/12対象メールのdedup keyが当時と同じ計算結果になるか。"
      },
      {
        "hypothesis": "IMAP再走査条件の不具合により、過去メールを広範囲再FETCHし、その際dedup判定が一部無効化された。",
        "evidence_to_check": "6/14実行時のIMAP search条件(SINCE/UID範囲)、FETCH_LIMIT変更、last_uid保存値の巻き戻り、UIDVALIDITY変更、Cron多重起動、同一メールが同一run内で2回見えたか、サーバ側フォルダ移動や再同期有無。"
      },
      {
        "hypothesis": "dedupキー設計不備。Message-ID未使用/不安定で、件名・送信者・時刻の組み合わせや本文抽出差分により同一メールを別物と判定した。",
        "evidence_to_check": "当該2件の保存データでmessage_idが空か、正規化前後で差異があるか、本文hashやsubject normalize結果が異なるか、1時間差で2件入ったrunのログでdedup miss理由が記録されているか。"
      }
    ],
    "investigation_order": [
      "1. 6/14 16:04 UTC と 17:03 UTC の2回実行ログを抽出し、同一メールがどのキーで新規扱いされたか確認する。",
      "2. 当該メールのRFC822 Message-ID、IMAP UID、INTERNALDATE、Date、folder を原本から取得し、Notion重複2件・5/27正本2件と突合する。",
      "3. processed_ids等のdedupストアを点検し、6/14直前の再初期化・欠損・フォーマット変更有無を確認する。",
      "4. IMAPの取得条件を確認し、last_uid巻き戻りやSINCE日付再走査、UIDVALIDITY変化がないか切り分ける。",
      "5. 6/14当日にデプロイ、env変更、Cron多重起動、ジョブ失敗後リトライがなかったか確認する。",
      "6. 過去インシデントと同型か比較し、spam filter欠落やFETCH_LIMIT拡張で広く拾っていないかを見る。",
      "7. 再発防止として dedup key を Message-ID優先 + 本文hash補助へ固定し、同一Message-ID再登録時は強制スキップ/警告にする。"
    ]
  },
  "q5_matching_accuracy_for_later": {
    "top3_hypotheses": [
      "必須スキル全○条件が想定以上に厳しく、表記ゆれ・同義語未吸収で大半がNG/REVIEW落ちしている。",
      "過去に『単価優先で広く拾う』運用から、実装上は厳密スキル判定へ戻っており、CEO認識とコード/設定が乖離している。",
      "並行スコア5未満など副条件が強く効き、単価適合者でもMATCHまで上がらずREVIEW止まりになっている。"
    ],
    "review_points": [
      "実コード/設定でMATCH条件を確認し、CEO証言どおり『単価優先』になっているか照合",
      "スキル正規化辞書、同義語、表記ゆれ吸収の有無を点検",
      "15名弱母集団それぞれが NG/REVIEW/MATCH のどの条件で落ちたか理由コードを出力",
      "単価条件・稼働率・並行スコア閾値の寄与度を確認",
      "REVIEWを通知対象に含めるべきか業務設計を再確認"
    ],
    "ses_caveat": "SESでは『厳密一致』より『まず提案可能か』が重視されやすいため、完全一致MATCHだけに絞ると母集団が極端に細る。後日見直しでは、MATCH/REVIEWの運用境界と営業現場の期待値を合わせることが重要。"
  }
}
