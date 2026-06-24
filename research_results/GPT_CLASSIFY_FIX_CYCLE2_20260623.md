# 分類精度修正 サイクル2 GPT-5.4分析
Date: 2026-06-23

```json
{
  "root_cause": "skip先行確定を全面廃止したため、金額・稼働開始月・技術タグを含む『人材紹介メール』がprojectスコアに吸い込まれた。 engineer判定を eng>=4 かつ eng>=proj+2 に厳格化しすぎたため、候補者明示メールがunknownへ落ち、project/unknown悪化を誘発した。 つまり失敗点は『高確度engineerシグナルの救済不足』と『skip系候補者メールへの再ゲート不足』の2点。",
  "fixes": [
    {
      "id": "FIX-1",
      "problem": "skip→project が倍増。人材メールが project に流入している",
      "change": "skip先行確定を完全復活ではなく『高確度 engineer/要員テンプレート限定』で部分復活する。 classify() の project最終判定前に以下の pre-skip gate を追加する。\n\n```ts\nconst STRONG_ENGINEER_SUBJECT_PATTERNS = [\n  /(?:注力要員|要員情報|要員紹介|人材紹介|ご紹介人材|紹介可能要員|提案可能要員)/i,\n  /(?:\\d{1,2}歳|歳\\/|年齢[:：]?\\d{2}|男性|女性)/,\n  /(?:稼働可|即日可|参画可|提案可|常駐可|出社可)/,\n  /(?:Java|PHP|Python|Go|C#|VB\\.net|VBA|SQL|AWS|Spring|React)[^\\n]{0,20}(?:\\d年|経験)/i,\n  /(?:単価|万円|万～|〜\\d{2,3}万|\\d{2,3}万[円]?)/,\n  /(?:個人事業主|BP|1名|SE|PG|エンジニア)/i\n];\n\nfunction isStrongEngineerCandidateMail(subject:string, body:string){\n  const text = `${subject}\\n${body}`;\n  let hit = 0;\n  if (/(注力要員|要員情報|要員紹介|人材紹介|ご紹介人材|紹介可能要員|提案可能要員)/i.test(text)) hit += 3;\n  if (/(\\d{1,2}歳|年齢[:：]?\\d{2}|男性|女性)/.test(text)) hit += 2;\n  if (/(稼働可|即日可|参画可|提案可|常駐可|出社可)/.test(text)) hit += 2;\n  if (/(Java|PHP|Python|Go|C#|VB\\.net|VBA|SQL|AWS|Spring|React)[^\\n]{0,20}(\\d年|経験)/i.test(text)) hit += 2;\n  if (/(単価|万円|万～|〜\\d{2,3}万|\\d{2,3}万)/.test(text)) hit += 1;\n  if (/(個人事業主|BP|1名|SE|PG|エンジニア)/i.test(text)) hit += 1;\n  return hit >= 5;\n}\n\nif (isStrongEngineerCandidateMail(subject, body) && projectScore < engineerScore + 2) {\n  return 'skip';\n}\n```\n\n重要: 『元請け直』『案件』『募集』『開発支援』『導入支援』『○○PJ』など project 強シグナルが2個以上ある場合は pre-skip gate を発火させない。\n```ts\nconst strongProjectHits = countMatch(text, [/(案件|募集|開発支援|導入支援|保守支援|PJ|プロジェクト|業務支援|元請け直)/i]);\nif (isStrongEngineerCandidateMail(subject, body) && strongProjectHits < 2 && projectScore < engineerScore + 2) return 'skip';\n```",
      "expected_impact": "skip→project を大幅圧縮。人材テンプレートを再度 skip へ戻しつつ、案件明示メールは project に残せるため skip→project を 40/250 → 10以下に下げる見込み。"
    },
    {
      "id": "FIX-2",
      "problem": "engineer厳格化により project→unknown と engineer→unknown が増加",
      "change": "engineer判定に『候補者明示の救済ルート』を追加する。既存の eng>=4 && eng>=proj+2 を維持しつつ、下記の direct-candidate override を追加する。\n\n```ts\nfunction hasDirectCandidateMarker(text:string){\n  return /(?:\\bSE\\b|\\bPG\\b|エンジニア|要員|人材|候補者|技術者)/i.test(text)\n    && /(?:\\d{1,2}歳|男性|女性|所属|国籍|並行状況|稼働可|参画可|面談可|単価|経験|スキルシート)/.test(text);\n}\n\nfunction hasEngineerHeadline(subject:string){\n  return /(?:直個人|新着|要員|人材|ご紹介).{0,20}(?:SE|PG|エンジニア|要員)|(?:SE|PG|エンジニア).{0,20}(?:\\d{1,2}歳|男性|女性)/i.test(subject);\n}\n\nif ((hasDirectCandidateMarker(text) && engineerScore >= 3 && projectScore <= engineerScore + 1)\n    || (hasEngineerHeadline(subject) && engineerScore >= 2 && projectScore <= engineerScore + 1)) {\n  return 'engineer';\n}\n```\n\nこれにより『★新着★直個人【Goエンジニア 26歳/男性/6月~】』『VBA×Power BI｜業務改善・DX推進を一人称で担えるSE』のような候補者明示件名を unknown に落とさない。",
      "expected_impact": "engineer→unknown 6件の大半を解消し、project→unknown も一部回復。project→engineer 改善を壊さずに engineer の取りこぼしだけ救済できる。"
    },
    {
      "id": "FIX-3",
      "problem": "project→engineer 改善は達成したが、今後の閾値緩和で再悪化するリスクがある",
      "change": "engineer救済時にも『案件語の強い束』がある場合は engineer に倒さないガードを追加する。\n\n```ts\nconst HARD_PROJECT_PATTERNS = [\n  /(?:案件|募集案件|増員案件|開発支援|保守支援|導入支援|製造工程|基本設計|詳細設計|試験工程)/i,\n  /(?:勤務地|作業場所|リモート併用|面談\\d回|契約形態|精算幅|商流|外国籍可)/,\n  /(?:元請け|エンド|顧客先|PJ|プロジェクト)/i\n];\nconst hardProjectHitCount = countPatternHits(text, HARD_PROJECT_PATTERNS);\n\nconst blockEngineerOverride = hardProjectHitCount >= 3 && !/(\\d{1,2}歳|男性|女性|所属|候補者|人材紹介|要員紹介)/.test(text);\nif (blockEngineerOverride) {\n  // direct-candidate override を無効化\n}\n```\n\nさらに engineer score 加点のうち『単価』『開始月』『技術名』のように project でも出る汎用語は重みを下げる。代わりに『年齢・性別・所属・稼働可・要員紹介』など人材専用語の重みを上げる。\n例:\n```ts\nWEIGHT.engineer.genericTech = 1; // 旧2\nWEIGHT.engineer.rate = 0.5;      // 旧1\nWEIGHT.engineer.ageGender = 2;   // 旧1\nWEIGHT.engineer.availability = 2;// 旧1\nWEIGHT.engineer.staffingWord = 3;// 新設\n```",
      "expected_impact": "project→engineer の再悪化を防ぎつつ engineer救済のみを限定実行できる。22/400の改善を維持しやすい。"
    },
    {
      "id": "FIX-4",
      "problem": "project→unknown が増えており、project最終確定条件が弱い",
      "change": "unknown に落とす前に『案件構造』が揃っているメールを project に救済する fallback を追加する。\n\n```ts\nfunction hasProjectStructure(text:string){\n  let s = 0;\n  if (/(案件|募集|開発支援|導入支援|保守支援|PJ|プロジェクト)/i.test(text)) s += 2;\n  if (/(勤務地|作業場所|最寄|リモート|常駐)/.test(text)) s += 1;\n  if (/(面談\\d回|精算|単価|募集人数|開始時期|期間|契約形態)/.test(text)) s += 1;\n  if (/(必須スキル|尚可|業務内容|工程|環境)/.test(text)) s += 2;\n  return s >= 4;\n}\n\nif (currentLabel === 'unknown' && hasProjectStructure(text) && !hasDirectCandidateMarker(text)) {\n  return 'project';\n}\n```\n\nこれにより engineer厳格化の副作用で unknown 落ちした案件メールを project に戻す。",
      "expected_impact": "project→unknown を 29/400 → 20前後まで圧縮。engineer誤爆を抑えつつ案件メールの unknown 落ちを減らす。"
    },
    {
      "id": "FIX-5",
      "problem": "skip/project/engineer の判定順変更が副作用を生みやすく、再発防止策がない",
      "change": "判定ログを必須化し、誤分類クラスごとの feature hit を可視化する。最低限以下をログ出力する。\n\n```ts\nreturn {\n  label,\n  scores: { skipScore, engineerScore, projectScore },\n  flags: {\n    strongEngineerCandidate: isStrongEngineerCandidateMail(subject, body),\n    directCandidate: hasDirectCandidateMarker(text),\n    engineerHeadline: hasEngineerHeadline(subject),\n    projectStructure: hasProjectStructure(text),\n    hardProjectHitCount\n  },\n  matchedPatterns: matchedPatternIds\n};\n```\n\n加えて回帰防止テストを追加:\n- skip should win: 『【7月/注力要員】Java3年/SpringBoot/55〜58万』\n- skip should win: 『【PMO/7月稼働】システム更改に強み◆30歳（60万〜）』\n- skip should win: 『【関西要員/7月】VB.net/SQL/50万/常駐可』\n- project should win: 『【元請け直】大学向けデジタル証明書SaaS開発支援/〜100万【Roots案件】』\n- engineer should win: 『★新着★直個人【Goエンジニア 26歳/男性/6月~】』\n- engineer should win: 『【VBA×Power BI｜業務改善・DX推進を一人称で担えるSE】』",
      "expected_impact": "次サイクルで『どの条件が誤作動したか』を即時に把握でき、局所修正で回せる。今回のような一部改善・一部悪化の原因追跡コストを大幅に削減。"
    }
  ],
  "target": {
    "project_engineer": "≤25/400",
    "skip_project": "≤10/250",
    "project_unknown": "≤20/400",
    "engineer_unknown": "≤1/31"
  }
}
```