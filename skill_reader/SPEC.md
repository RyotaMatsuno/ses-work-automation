# SPEC.md - skill_reader

## 概要
スキルシート（PDF/Word/画像、フォーマット不問）を Claude API で読み取り、
案件DBの必須・尚可スキルと照合して ○×を自動生成する。

---

## 処理フロー

```
入力（ファイルパス or base64）
  ↓
① ファイル種別判定（PDF / Word / 画像）
  ↓
② テキスト抽出 または 画像化
  - PDF: pdfplumber でテキスト抽出 → 取れなければ画像変換
  - Word: python-docx でテキスト抽出
  - 画像（PNG/JPG）: そのまま
  ↓
③ Claude API でスキル抽出
  - system: 「SESのスキルシートからスキル一覧をJSON形式で返せ」
  - user: テキスト or base64画像を渡す
  - 出力: {"name": "...", "skills": ["Java", "Spring", ...], "years": {...}}
  ↓
④ 案件DBから募集中案件を取得（Notion API）
  ↓
⑤ 必須・尚可スキルと照合して ○× 生成
  ↓
⑥ 結果出力（JSON + コンソール表示）
  オプション: Notion エンジニアDBのスキル欄を更新
```

---

## 入力仕様

| 引数 | 説明 |
|---|---|
| `--file` | ローカルファイルパス（PDF/docx/png/jpg） |
| `--base64` | base64エンコード済みデータ（LINE/メール連携用） |
| `--mime` | MIMEタイプ（base64使用時必須: application/pdf, image/png 等） |
| `--engineer-id` | NotionエンジニアページID（指定時はDB更新も行う） |
| `--projects` | 照合対象案件を絞る（カンマ区切りの案件名部分一致） |

---

## Claude API プロンプト設計

### system
```
あなたはSES業界のスキルシート解析AIです。
入力されたスキルシートから以下をJSON形式で抽出してください。
出力はJSON のみ。前後に説明文不要。

{
  "name": "氏名（イニシャルでも可）",
  "skills": ["スキル名1", "スキル名2", ...],
  "experience_years": {"Java": 5, "Python": 3, ...},  // 年数が読み取れる場合のみ
  "level": "上級SE|SE|上級PG|PG",  // 経験年数・工程から推定
  "summary": "一言サマリー（50文字以内）"
}

スキル名は以下の標準名に統一すること:
Java, Python, PHP, JavaScript, TypeScript, C#, C言語, COBOL,
Node.js, React, Vue.js, Spring, Laravel, Ruby, Go, Swift,
AWS, Azure, GCP, Docker, Kubernetes, Linux,
Oracle, MySQL, PostgreSQL, MongoDB,
インフラ, NW設計, セキュリティ, PMO, PM, 要件定義, 基本設計, 詳細設計
```

---

## 照合ロジック

- 必須スキルが1つでも ✕ → 提案不可フラグ
- 必須全○ + 尚可50%以上 → 上振れ単価提案可
- 必須全○ + 尚可50%未満 → 案件予算内提案

---

## 出力例（コンソール）

```
【スキルシート解析結果】
氏名: R.H（24歳・男性）
抽出スキル: Java, PostgreSQL, Linux, Spring
推定レベル: SE
一言: Java/PostgreSQL メインの即日稼働可能SE

【照合結果】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
案件: Struts Java 基本設計〜 70万（ICD）
  必須: Java:○
  尚可: なし
  → 提案可 ✅（粗利22万）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
案件: 基幹システム移行 Java/Spring/Postgre 75万（Roots）
  必須: Java:○  PostgreSQL:○
  尚可: なし
  → 提案可 ✅（粗利27万）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## テスト方針
1. サンプルPDFでスキル抽出が正しいか確認
2. 必須スキル照合ロジックの正確性確認
3. 画像スキルシート（読み取りにくいフォーマット）での精度確認
