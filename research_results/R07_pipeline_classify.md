# R07: mail_pipeline 分類ロジック調査
調査日: 2026-06-18

## 結論（1行）
Phase 2のRecall重視化は事務・ヘルプデスク案件の取りこぼし解消に有効だが、`ENGINEER_PATTERNS`の`【BTM|【NBW`誤マッチと請求書・契約書のskip欠落が案件漏れ・ノイズの主リスク。

## 分類パターン一覧

### classify_system プロンプト全文（mail_pipeline.py L603-624）

```
あなたはSES業界のメール分類AIです。
件名と本文冒頭からemail_typeを判定し、JSONのみで返してください。

形式: {"type": "project"|"skip"}
※engineerは廃止。人員紹介メールはskipに統合

分類ルール:
- project: 業務委託・SES・派遣の案件情報。開発案件だけでなく、
  事務、ヘルプデスク、PMO、運用監視、キッティング、情シス支援、
  テスト、データ入力、コールセンター等も全て「project」。
  「案件」「募集」「○万」「○月〜」等のキーワードがあればproject。
  迷ったらprojectにする（Recall最優先）。
- skip: 以下は全てskip
  ・エンジニア/技術者/人材の紹介メール（「弊社エンジニア」「要員ご紹介」等）
  ・セミナー案内、メルマガ、配信停止通知、自動返信
  ・営業挨拶（案件情報なし）、求人広告、ニュースレター
  ※人員は松野/岡本がLINE経由で手動登録するため、配信の人員紹介は不要

SES業界用語:
- BP/プロパー/商流/稼働/並行 = SES業界の一般用語
- 案件 = 業務委託の仕事依頼
- 要員/人材 = エンジニア紹介
```

### analyze_final.py ルールベース判定（全列挙）

**判定関数 `classify_by_rule(subj, frm)` の優先順位: skip → engineer → project → unknown**

| カテゴリ | パターン | 検索対象 |
|---|---|---|
| SKIP (5) | セミナー\|ウェビナー\|説明会\|メルマガ\|配信停止\|プレスリリース\|ニュースレター | subj + frm |
| SKIP | 自動返信\|Auto-Reply\|Out of office\|自動応答\|不在通知 | subj + frm |
| SKIP | サービス.*ご紹介\|導入事例\|資料請求\|無料.*トライアル\|キャンペーン | subj + frm |
| SKIP | 採用情報\|正社員募集\|求人.*正社員\|転職.*支援 | subj + frm |
| SKIP | 営業挨拶\|ご挨拶のみ | subj + frm |
| ENGINEER (21) | 【直人材】\|【直要員】\|【直個人】\|【直BP】\|【SPONTO直個人】 | subj + frm[:50] |
| ENGINEER | 【弊社\|弊社.*プロパー\|弊社.*社員\|弊社.*フリー\|弊社.*個人\|弊社実績 | subj + frm[:50] |
| ENGINEER | 【要員】\|【人材】\|【要員配信】\|【人材情報】\|注力要員\|人材情報\|要員ご紹介 | subj + frm[:50] |
| ENGINEER | 弊社エンジニア\|技術者.*ご紹介\|エンジニア.*ご紹介 | subj + frm[:50] |
| ENGINEER | 【Astro人材】\|【プラウド要員】\|【KAD\|【ビズリンク\|【GLITTERS\|**【BTM\|【NBW**\|【アイル要員\|【SPONTO\|【実績あり所属 | subj + frm[:50] |
| ENGINEER | [／/](?:[0-9]+歳\|[0-9]+年).*(?:男性\|女性) | subj + frm[:50] |
| ENGINEER | (?:男性\|女性)／.*(?:万円\|万$\|\d+万) | subj + frm[:50] |
| ENGINEER | 即日.*(?:要員\|参画\|稼働)\|(?:要員\|参画).*即日\|稼働.*可能\|空き.*あり | subj + frm[:50] |
| ENGINEER | 【即日要員】\|即〜【\|即日【 | subj + frm[:50] |
| ENGINEER | 【[0-9]月.*要員】\|[0-9]月.*要員.*紹介\|要員.*[0-9]月 | subj + frm[:50] |
| ENGINEER | 【(?:Java\|Python\|…\|Tableau).*[0-9]+年】 | subj + frm[:50] |
| ENGINEER | (?:Java\|Python\|…\|COBOL).*[／/][0-9]+歳 | subj + frm[:50] |
| ENGINEER | [0-9]+万.*エンジニア\|エンジニア.*[0-9]+万\|[～〜~][0-9]+万\|… | subj + frm[:50] |
| ENGINEER | @[0-9]+万\|／[0-9]+万\|・[0-9]+万\|/[0-9]+万 | subj + frm[:50] |
| ENGINEER | 単価下げ\|条件緩和\|単価調整\|単価.*相談 | subj + frm[:50] |
| ENGINEER | 常駐可.*(?:弊社\|当社\|PM\|PMO\|Java\|インフラ)\|【実績あり | subj + frm[:50] |
| ENGINEER | [A-Z]{2,4}[0-9]{3,4}のご紹介\|のご紹介です | subj + frm[:50] |
| ENGINEER | ★大特価\|大特価 | subj + frm[:50] |
| ENGINEER | 【Java/C#人材】\|【Java.*人材】\|【.*人材】(?=.*万) | subj + frm[:50] |
| ENGINEER | 増員枠\|弊社増員 | subj + frm[:50] |
| PROJECT (12) | 【案件】\|【案件情報】\|【PJ】\|【プロジェクト】\|【求人】 | **subjのみ** |
| PROJECT | 案件.*募集\|募集.*案件\|案件.*紹介\|紹介.*案件 | subjのみ |
| PROJECT | CONVICTION案件\|NBW案件\|BTM案件\|【.*案件情報】\|【.*注力案件】\|【.*案件一覧】\|ICD案件 | subjのみ |
| PROJECT | 【.*(?:開発\|設計\|構築\|運用\|保守\|移行\|刷新\|導入\|リプレース\|DX\|PMO\|ヘルプデスク\|キッティング\|情シス\|テスト\|データ入力\|監視).*】 | subjのみ |
| PROJECT | 元請け\|直案件\|エンド直\|元請直\|エンド顧客\|現場直\|商流 | subjのみ |
| PROJECT | [0-9]+月[〜～~/\-] | subjのみ |
| PROJECT | **[0-9]+万** | subjのみ |
| PROJECT | ヘルプデスク\|PMO\|コールセンター\|事務\|運用監視\|キッティング\|情シス\|データ入力 | subjのみ |
| PROJECT | ≪急募≫\|《急募》\|★.*ICD案件 | subjのみ |
| PROJECT | COBOL案件\|汎用系.*案件\|若手歓迎.*案件 | subjのみ |
| PROJECT | 業務委託\|SES\|派遣 | subjのみ |

### 事業ルール照合表

| パターン | ルール判定 | LLM判定 | 正しい分類 | 実装OK? |
|---|---|---|---|---|
| SES案件メール（開発） | project（【案件】等） | project | project | OK |
| ヘルプデスク・事務 | project（ヘルプデスク\|事務等） | project | project | OK（Phase 2で改善） |
| PMO・コンサル | project（PMO等） | project | project | OK |
| 急募 | project（≪急募≫等） | project | project | OK |
| 面談設定済み | unknown→LLM | project（Recall） | project | △（件名に面談キーワードなし） |
| 人員紹介（【要員】等） | engineer→**skip** | skip | skip | OK |
| 人員紹介（弊社エンジニア） | engineer→skip | skip | skip | OK |
| BTM/NBWブランド**案件** | **engineer→skip**（`【BTM`/`【NBW`誤マッチ） | —（LLM未到達） | project | **NG** |
| 営業メール・広告 | skip（セミナー/メルマガ等） | skip | skip | OK |
| 自動返信 | skip | skip | skip | OK |
| 請求書・契約書 | unknown→LLM | skip（指示あり） | skip | △（ルール未カバー、LLM依存） |
| 自社内部メール | unknown→LLM | 不明（挨拶のみ） | skip | △（専用パターンなし） |
| 正社員求人 | skip | skip | skip | OK |
| 地方案件 | unknown→LLM | project（Recall） | project | OK（旧版は地方=skipで漏れ） |
| ロースキル・コールセンター案件 | project | project | project | OK（旧版はskipで漏れ） |
| 案件+人材混在メール | **engineer優先→skip** | — | project（案件部分） | **NG**（取りこぼし） |
| 挨拶のみ（お世話になっております） | unknown→LLM | project（Recall指示） | skip | △（ノイズリスク） |

## 人員紹介メールのskip判定

### ルール側
- `ENGINEER_PATTERNS`（21パターン）で件名+送信者先頭50文字を検索
- マッチ時は `classify_email_v2` で即 `{"type":"skip"}`（LLM分類をスキップ）
- 主なキーワード: 【要員】【人材】、弊社エンジニア、年齢/性別/万円の組み合わせ、即日要員、スキル+年数ブラケット等

### LLM側
- `classify_system` に明示: 「エンジニア/技術者/人材の紹介メール → skip」「要員/人材 = エンジニア紹介」
- LLM分類結果で `engineer` / `other` / `skip` はすべて `skip` に正規化（L758-759）

### すり抜けパターン（案件と人員混在）
1. **優先順位問題**: `classify_by_rule` は engineer を project より先に判定。件名に【要員】と【案件】が両方ある場合、engineer→skipとなり案件部分が捨てられる
2. **BTM/NBW案件の誤判定**: `【BTM案件】` / `【NBW案件】` が `【BTM` / `【NBW` パターンに先行マッチし、案件メールがskip化（**重大**）
3. **本文のみに人員情報**: ルールは件名のみ（PROJECT）または件名+送信者（ENGINEER）。件名が無難で本文に要員情報のみの場合、unknown→LLM。Recall指示によりproject誤判定の可能性
4. **engineer_system は残存**: コード上は未使用（v6.0 mainでengineer登録なし）だが、Batch APIフォールバック `classify_email()` は依然3分類（project/engineer/other）

## Phase 2緩和の影響分析

Phase 2 = v6.0改修（`done_tasks/20260618_180907_pipeline_full_intake.md`）。旧版は `analyze_v3.py` / `mail_pipeline.py.bak_phase4` を基準に比較。

### 旧SKIP → 新PROJECT になったカテゴリ

| 旧（skip） | 新（project/unknown→LLM project） | 根拠 |
|---|---|---|
| 地方案件（関西・大阪・福岡等） | unknown→LLM project | SKIP_PATTERNSから地方削除 |
| ロースキル・未経験可・アポ取り | project | SKIPから削除、PROJECTにヘルプデスク等追加 |
| コールセンター（業務系） | project | 同上 |
| ヘルプデスク・事務・情シス・キッティング | project | PROJECT_PATTERNSに明示追加 |
| PMO（単独） | project | PROJECT_PATTERNSに追加 |
| `[0-9]+万` のみの件名 | project（ルール） | PROJECT_PATTERNS新規追加 |
| `[0-9]+月〜` のみの件名 | project（ルール） | PROJECT_PATTERNS新規追加 |
| SES/派遣/業務委託 | project（ルール） | PROJECT_PATTERNS新規追加 |
| LLM: 迷った場合 | 旧: other/skip | 新: **project（Recall最優先）** |

### 緩和しすぎてノイズが入るケース

| リスク | 説明 |
|---|---|
| Recall指示の過剰project化 | 「迷ったらproject」により挨拶のみ・社内連絡がNotion登録される可能性 |
| `[0-9]+万` projectルール | 件名に万円のみで業務内容不明でもproject確定（ただしengineerが先に判定されるため人員系は除外） |
| `業務委託\|SES\|派遣` | 契約・請求関連メールの件名に「業務委託契約」等が含まれるとproject誤判定の可能性 |
| 請求書・契約書 | 旧v6.16には `SUBJECT_SKIP_PATTERNS`（請求書/契約書等）があったが、**現行v6.0のanalyze_finalには未移植** |
| Batchフォールバック | API障害時 `classify_email()` が旧3分類プロンプトに戻り、engineer/other処理が不整合 |

## エッジケース分析

| ケース | 現行の挙動 | 問題 |
|---|---|---|
| 件名が空 | ルール: unknown → LLM分類（件名空+本文100字） | 本文依存。Recall指示でproject化リスク |
| 本文が極端に短い | ルール: 件名のみ判定。LLM: body[:100] | 本文情報がほぼ使えない |
| HTML onlyメール | `get_body_and_attachments()` は **text/plain のみ**取得。HTMLフォールバックなし | body="" → 件名のみ依存。HTML主体メールは分類精度低下 |
| 転送（Fw:）/ 返信（Re:） | プレフィックス除去なし。件名そのままマッチ | 通常は問題少。元件名のパターンは有効 |
| 添付のみ・本文なし | body=""、添付は分類に未使用 | 件名が無難だとunknown→LLM。スキルシート添付の人員メールはすり抜け可能性 |
| BTM/NBW案件メール | engineer誤マッチ→skip | **案件取りこぼし（確認済みパターン）** |
| API Key未設定 | `classify_email()` フォールバック（旧3分類） | project/skip 2値運用と不整合 |
| Batch API障害 | 同上フォールバック | 分類基準が一時的に旧版に戻る |

## LLM分類とルール分類の競合時の優先順位

```
classify_email_v2 フロー:

1. classify_by_rule(subject, sender)
   ├─ skip      → 即 skip（LLM不要）
   ├─ engineer  → 即 skip（LLM不要）※v6.0でengineer=skip統合
   ├─ project   → 即 project構造化（classify LLM不要、extract LLMのみ）
   └─ unknown   → classify_system LLM（body[:100]）

2. LLM classify結果（unknownのみ）
   ├─ skip / other / engineer → skip
   └─ project → project構造化（第2バッチ）

優先原則: ルール判定が先。ルールで確定した場合LLMは呼ばれない。
→ ルール誤判定（BTM案件→engineer等）はLLMで救済されない。
```

mainループ（L1583-1587）での最終処理:
- `info.get("type")` が `engineer` の場合も `skip` に正規化
- `project` のみ Notion登録・マッチング実行
- それ以外（skip/other/error）は破棄

## 推奨アクション

- [ ] **P0**: `ENGINEER_PATTERNS` の `【BTM|【NBW` を `【BTM要員|【BTM人材|【NBW要員|【NBW人材` 等に限定し、`【BTM案件】`/`【NBW案件】` の誤skipを修正
- [ ] **P0**: 件名に `案件` を含む場合は engineer より project を優先する例外ルールを `classify_by_rule` に追加（混在メール対策）
- [ ] **P1**: v6.16にあった `SUBJECT_SKIP_PATTERNS`（請求書・契約書・勤怠・見積等）を `SKIP_PATTERNS` に復活
- [ ] **P1**: `get_body_and_attachments()` に text/html → プレーンテキスト変換フォールバックを追加（HTML onlyメール対策）
- [ ] **P2**: Batchフォールバック `classify_email()` を現行2値プロンプト（classify_system）に統一
- [ ] **P2**: `Fw:`/`Re:`/`[再送]` プレフィックス除去を分類前に実施
- [ ] **P2**: 分類精度モニタリング — raw_inbox.db の `classify_result` + `note` フィールドでルール/LLM別の誤判定率を週次集計
- [ ] **P3**: Recall指示を「案件キーワード（案件/募集/万/月〜/SES）がない挨拶のみはskip」に細分化し、ノイズ登録を抑制
