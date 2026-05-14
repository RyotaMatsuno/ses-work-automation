"""
ai_extractor.py - Claude APIでスキルシートから構造化データ抽出モジュール
"""
import json
import logging
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
logger = logging.getLogger(__name__)

SKILL_OPTIONS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js", "React",
    "AWS", "インフラ", "PostgreSQL", "Oracle", "Vue.js", "MySQL", "Swift", "Azure",
    "Linux", "Go", "Ruby", "Docker", "MongoDB", "Spring"
]

SYSTEM_PROMPT = f"""あなたはSESエンジニアのスキルシートから情報を抽出するAIです。
以下のテキストから全エンジニアの情報を抽出し、JSON配列で返してください。
JSON以外のテキストは一切出力しないでください。

抽出するJSON形式:
[
  {{
    "name": "氏名（フルネーム）",
    "price": 単価の数値（万円、不明はnull）,
    "available_date": "稼働可能日（YYYY-MM-DD形式、即日は今日の日付、不明はnull）",
    "experience_years": 経験年数の数値（不明はnull）,
    "skills": ["スキル1", "スキル2", ...]
  }}
]

スキルは以下のリストから該当するものだけを選んでください:
{", ".join(SKILL_OPTIONS)}
"""


def extract_engineers(text: str, filename: str) -> list:
    """
    スキルシートテキストからエンジニア情報をClaude APIで抽出。

    Returns:
        list of dict: [{"name", "price", "available_date", "experience_years", "skills"}, ...]
        失敗時は空リスト
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が .env に設定されていません")

    client = anthropic.Anthropic(api_key=api_key)

    today = date.today().isoformat()
    user_content = f"今日の日付: {today}\n\n以下のスキルシートから情報を抽出してください:\n\n{text[:8000]}"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}]
        )
        raw = response.content[0].text.strip()

        # ```json ... ``` のfenceを除去
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        engineers = json.loads(raw)
        if not isinstance(engineers, list):
            engineers = [engineers]

        logger.info(f"抽出成功: {filename} → {len(engineers)}名")
        return engineers

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失敗: {filename} - {e}")
        return []
    except Exception as e:
        logger.error(f"Claude API呼び出し失敗: {filename} - {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = """
氏名: 山田太郎
経験年数: 5年
希望単価: 65万円
稼働可能: 即日
スキル: Java, Spring, Oracle, Linux
"""
    result = extract_engineers(sample, "sample.txt")
    print(json.dumps(result, ensure_ascii=False, indent=2))
