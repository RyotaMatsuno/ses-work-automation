import re

path = r"matching_v3\structurer.py"
with open(path, encoding="utf-8") as f:
    src = f.read()

old_prompt = '''SYSTEM_PROMPT = """あなたはSES（System Engineer Staffing）案件メールからJSON情報を抽出するアシスタントです。
メール本文を読み、指定されたJSONスキーマに従って情報を抽出してください。

ルール:
- 有効なJSONのみ出力する。説明文やMarkdownコードブロックを含めない
- 読み取れないフィールドはnullまたは空配列
- required_skills: 必須・必要と明記されたスキルのみ
- optional_skills: 尚可・歓迎と明記されたスキル
- ambiguous_skills: 分類困難・一般的すぎるスキル（例: "クラウド経験"）
- price_min/max: 万円単位の数値（"〜60万"なら max=60.0, min=null）
- extraction_confidence: 抽出の確信度（不明点が多い場合は低く）"""'''

new_prompt = '''SYSTEM_PROMPT = """あなたはSES（System Engineer Staffing）案件メールからJSON情報を抽出するアシスタントです。
メール本文を読み、指定されたJSONスキーマに従って情報を抽出してください。

ルール:
- 有効なJSONのみ出力する。説明文やMarkdownコードブロックを含めない
- 読み取れないフィールドはnullまたは空配列
- required_skills: 必須・必要と明記されたスキルのみ。具体的な技術・ツール名（Git, Slack, Backlog, MuleSoft, Salesforce, SQL, Terraform等）は必ずrequired_skillsに入れる
- optional_skills: 尚可・歓迎と明記されたスキル
- ambiguous_skills: ソフトスキル・抽象的な表現のみ（例: "クラウド経験", "コミュニケーション能力", "主体性", "リーダー経験", "AI利活用", "技術力"等）。具体的なツール名・技術名はambiguous_skillsに入れない
- price_min/max: 万円単位の数値（"〜60万"なら max=60.0, min=null）
- extraction_confidence: 抽出の確信度（不明点が多い場合は低く）"""'''

if old_prompt in src:
    new_src = src.replace(old_prompt, new_prompt)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("OK: SYSTEM_PROMPT updated")
else:
    print("NG: old_prompt not found")
    # 現在のSYSTEM_PROMPTを表示
    m = re.search(r'SYSTEM_PROMPT = """.*?"""', src, re.DOTALL)
    if m:
        print("Current SYSTEM_PROMPT:\n", m.group()[:300])
