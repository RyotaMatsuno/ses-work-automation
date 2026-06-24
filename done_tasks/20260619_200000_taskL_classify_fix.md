# 【Cursor作業指示】Task L: 分類精度改善（other→project漏れ修正）【最優先】

対象ディレクトリ: ses_work/
作業内容: analyze_final.pyのルール分類を強化し、案件メールのother漏れを修正
完了条件: 下記テストケース全パス + 既存テスト全パス

緊急度: 高。141件の案件メールがother判定でNotion未登録になっている。

## 問題の全容

379件がother判定。内訳:
- 件名に案件含む: 141件 → 本来project
- 件名に要員/人材含む: 132件 → 本来skip
- その他: 106件 → ほぼ全部案件（単価・期間・勤務地表記から明らか）

## 原因

analyze_final.pyのPROJECT_PATTERNSが明確なプレフィックスしか拾えない。
SES業界で一般的な以下パターンが未対応:
1. 案件配信/案件募集 → unknownになる
2. 〜65万円等の単価表記 → engineer誤判定→skip
3. 7月〜/即日〜等の期間表記 → unknown
4. 募集/常駐/リモート/面談N回 → unknown

## 修正方針

### 1. classify_by_rule()にPROJECT優先判定を追加

件名に以下のキーワードがあればengineerより先にproject判定:
- 案件/募集/常駐/増員/面談/準委任/業務委託/決済者直/元請

単価表記+期間表記の組み合わせもproject:
- 単価: [0-9]{2,3}万 のパターン
- 期間: [0-9]月〜 や 即日〜

スコアリング: project_keyword + has_price + has_period >= 2 ならproject

### 2. AI分類のother判定を再チェック

classify_email_v2でAIがotherを返した場合、
件名に案件キーワードがあればprojectに昇格させる。

### 3. other再分類バッチ

raw_inbox.pyに reset_other_for_reclassify() を追加:
other判定かつ件名に案件キーワードを含むレコードのprocessed=0にリセット。
修正後のルールで再分類される。

## テストケース

- 【案件配信】7月〜/UiPath案件 → project
- 【フルリモート/〜65万円/TypeScript】AI開発 → project
- 決済者直【C/C++/常駐】→ project
- 【8月開始】購買管理PL/SQL募集（4名）→ project
- ★フルリモート!【Go / 80万〜90万】EC開発 → project
- 【SES交流会】つながりが次の案件をつくる → skip
- 【イルミナ：要員】M.N（29歳）→ skip
- 【BTM案件】Go/基本リモート → project
- お世話になっております → unknown

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
- Recall最優先: 案件を見落とすよりskipすべきものをprojectにする方がマシ
