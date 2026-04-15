import requests
import json
import os

API_KEY = "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"
PAGE_ID = "343450ff-37c0-80a8-9707-fc29109b057a"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def create_engineer_db():
    data = {
        "parent": {"type": "page_id", "page_id": PAGE_ID},
        "title": [{"type": "text", "text": {"content": "エンジニアDB"}}],
        "properties": {
            "名前": {"title": {}},
            "スキル": {"multi_select": {"options": [
                {"name": "Java", "color": "blue"},
                {"name": "Python", "color": "green"},
                {"name": "PHP", "color": "purple"},
                {"name": "JavaScript", "color": "yellow"},
                {"name": "TypeScript", "color": "orange"},
                {"name": "C#", "color": "red"},
                {"name": "Node.js", "color": "pink"},
                {"name": "React", "color": "gray"},
                {"name": "AWS", "color": "brown"},
                {"name": "インフラ", "color": "default"}
            ]}},
            "単価（万円）": {"number": {"format": "number"}},
            "稼働状況": {"select": {"options": [
                {"name": "稼働中", "color": "red"},
                {"name": "稼働可能", "color": "green"},
                {"name": "調整中", "color": "yellow"}
            ]}},
            "稼働可能日": {"date": {}},
            "経験年数": {"number": {"format": "number"}},
            "連絡先": {"phone_number": {}},
            "メール": {"email": {}},
            "備考（LINEメモ）": {"rich_text": {}}
        }
    }
    res = requests.post("https://api.notion.com/v1/databases", headers=headers, json=data)
    print("エンジニアDB:", res.status_code, res.json().get("id", res.json()))
    return res.json().get("id")

def create_project_db():
    data = {
        "parent": {"type": "page_id", "page_id": PAGE_ID},
        "title": [{"type": "text", "text": {"content": "案件DB"}}],
        "properties": {
            "案件名": {"title": {}},
            "必要スキル": {"multi_select": {"options": [
                {"name": "Java", "color": "blue"},
                {"name": "Python", "color": "green"},
                {"name": "PHP", "color": "purple"},
                {"name": "JavaScript", "color": "yellow"},
                {"name": "TypeScript", "color": "orange"},
                {"name": "C#", "color": "red"},
                {"name": "Node.js", "color": "pink"},
                {"name": "React", "color": "gray"},
                {"name": "AWS", "color": "brown"}
            ]}},
            "単価（万円）": {"number": {"format": "number"}},
            "開始日": {"date": {}},
            "期間": {"rich_text": {}},
            "クライアント": {"rich_text": {}},
            "勤務地": {"rich_text": {}},
            "リモート": {"select": {"options": [
                {"name": "フルリモート", "color": "green"},
                {"name": "一部リモート", "color": "yellow"},
                {"name": "常駐", "color": "red"}
            ]}},
            "ステータス": {"select": {"options": [
                {"name": "募集中", "color": "green"},
                {"name": "選考中", "color": "yellow"},
                {"name": "成約", "color": "blue"},
                {"name": "終了", "color": "gray"}
            ]}},
            "案件詳細": {"rich_text": {}}
        }
    }
    res = requests.post("https://api.notion.com/v1/databases", headers=headers, json=data)
    print("案件DB:", res.status_code, res.json().get("id", res.json()))
    return res.json().get("id")

if __name__ == "__main__":
    print("データベースを作成中...")
    engineer_id = create_engineer_db()
    project_id = create_project_db()
    print("\n完了！")
    print(f"エンジニアDB ID: {engineer_id}")
    print(f"案件DB ID: {project_id}")
