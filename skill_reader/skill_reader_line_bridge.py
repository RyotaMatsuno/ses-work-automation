"""
skill_reader_line_bridge.py
LINE WebhookからPDF/画像スキルシートを受信してskill_reader_api（8766）に橋渡しする。
webhook_server.pyのhandle_webhookから呼び出す。
"""
import requests, base64, os


SKILL_API_URL = "http://127.0.0.1:8766/process_skill_sheet"


def process_skill_sheet_from_line(b64_data: str, mime: str,
                                   affiliation: str = "貴社",
                                   engineer_price: int = None,
                                   engineer_id: str = None) -> dict:
    """
    skill_reader_api（8766）にスキルシートを送信して結果を受け取る。
    戻り値: {"status": "ok", "engineer": {...}, "iko_mail": "...", "just_count": N}
    """
    payload = {
        "base64": b64_data,
        "mime": mime,
        "affiliation": affiliation,
    }
    if engineer_price:
        payload["price"] = engineer_price
    if engineer_id:
        payload["engineer_id"] = engineer_id

    try:
        res = requests.post(SKILL_API_URL, json=payload, timeout=120)
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "message": f"API error {res.status_code}: {res.text[:200]}"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "skill_reader_api（8766）に接続できません。サーバーが起動しているか確認してください。"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def build_skill_result_message(result: dict) -> str:
    """skill_reader_apiのレスポンスをLINEメッセージに変換する"""
    if result.get("status") != "ok":
        return f"❌ スキルシート解析失敗: {result.get('message', '不明なエラー')}"

    eng = result.get("engineer", {})
    name = eng.get("name", "不明")
    skills = ", ".join(eng.get("skills", [])) or "なし"
    level = eng.get("level", "不明")
    summary = eng.get("summary", "")
    just_count = result.get("just_count", 0)

    msg = f"📋 スキルシート解析完了\n"
    msg += f"氏名: {name}\n"
    msg += f"レベル: {level}\n"
    msg += f"スキル: {skills}\n"
    if summary:
        msg += f"概要: {summary}\n"
    msg += f"\n粗利ジャスト案件（5〜12万）: {just_count}件\n"

    if just_count > 0:
        msg += "\n意向確認メール文面を生成しました。\n"
        msg += "「メール送信して xxx@yyy.com」で意向確認メールを送信できます。"
    else:
        msg += "\n提案可能案件はありますが粗利ジャスト案件はありません。\n"
        msg += "「メール送信して xxx@yyy.com」で意向確認メールを送信できます。"

    return msg
