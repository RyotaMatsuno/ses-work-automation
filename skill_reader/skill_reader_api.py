"""
skill_reader_api.py - ローカルAPIサーバー PORT:8766
LINE Webhookとmail_pipelineからskill_readerをHTTP経由で呼び出す。
"""

import base64
import os
import sys

# skill_readerモジュールのパスを追加
_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)

from flask import Flask, jsonify, request

from skill_reader import (
    extract_skills_from_image,
    extract_skills_from_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    generate_iko_mail,
    get_active_projects,
    match_skills,
    pdf_to_base64_image,
    update_engineer_notion,
)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "skill_reader_api"})


@app.route("/process_skill_sheet", methods=["POST"])
def process_skill_sheet():
    try:
        body = request.get_json(force=True)
        b64_data = body.get("base64", "")
        mime = body.get("mime", "application/pdf")
        price = body.get("price")
        affil = body.get("affiliation", "貴社")
        eng_id = body.get("engineer_id")

        if not b64_data:
            return jsonify({"status": "error", "message": "base64 required"}), 400

        raw = base64.b64decode(b64_data)
        info = None

        if mime == "application/pdf":
            text = extract_text_from_pdf(raw)
            if text:
                info = extract_skills_from_text(text)
            else:
                b64img = pdf_to_base64_image(raw)
                if b64img:
                    info = extract_skills_from_image(b64img, "image/png")
        elif "word" in mime:
            text = extract_text_from_docx(raw)
            info = extract_skills_from_text(text)
        elif mime.startswith("image/"):
            info = extract_skills_from_image(b64_data, mime)
        else:
            text = raw.decode("utf-8", errors="ignore")
            info = extract_skills_from_text(text)

        if not info:
            return jsonify({"status": "error", "message": "skill extraction failed"}), 500

        if eng_id:
            update_engineer_notion(eng_id, info)

        projects = get_active_projects()
        match_results = match_skills(info.get("skills", []), projects, price)
        iko_mail = generate_iko_mail(info, match_results, price, affil)
        just_count = sum(1 for r in match_results if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)

        return jsonify(
            {
                "status": "ok",
                "engineer": info,
                "match_results": match_results,
                "iko_mail": iko_mail,
                "just_count": just_count,
            }
        )

    except Exception as e:
        import traceback

        return jsonify({"status": "error", "message": str(e), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":
    print("skill_reader_api 起動: http://127.0.0.1:8766")
    app.run(host="127.0.0.1", port=8766, debug=False)
