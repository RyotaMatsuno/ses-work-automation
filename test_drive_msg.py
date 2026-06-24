import sys

sys.path.insert(0, ".")
from matching_v2.notify_line import build_project_message

proj = {
    "name": "テスト案件",
    "raw_body": "テスト本文",
    "project_url": "",
    "budget": 70,
}
cands = [
    {
        "engineer_info": {
            "name": "山田太郎",
            "raw_body": "人材テスト本文",
            "drive_url": "https://drive.google.com/file/d/TEST123/view",
            "price": 60,
            "parallel": "なし",
            "skills": ["Python"],
            "affiliation": "テスト所属",
        },
        "gross": 7,
    }
]

msg = build_project_message(proj, cands)
print(msg)
