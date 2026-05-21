import hmac, hashlib, base64, json, requests

secret = 'REDACTED-SECRET'
text = """これ原さんどうですか？
＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
【C#／.NET】某医療機器メーカー向けシステム開発案件
概要：
弊社が元請け（プライム）として参画している某医療機器メーカー向けのプロジェクトです。現在、弊社プロパーのリーダーを含め計10名が稼働中の安定したチーム体制での交代枠となります。C#を用いた設計から製造、結合テスト（IT）まで、一人称で自走いただけるエンジニアを募集いたします。
必須スキル：
・C#を用いた開発実務経験が3年以上ある方
・設計 〜 製造 〜 結合テストまで、各工程1年程度の実務経験を有し、一人称で動ける方
・円滑なコミュニケーション能力（チーム開発・報告・相談）
尚可スキル：
・Windowsサービス（バックグラウンド処理）の開発経験
・Java、またはTypeScriptの開発経験
・メンバーフォローやリーダー、サブリーダーの経験
〇期間：2026年6月 〜 長期
〇場所：新宿駅（常駐）
〇単価：60万円
〇精算：140 〜 180h（※160h中央割）
〇定時：8:45 ～ 17:30
〇面談：1回（WEB／上位決裁）
〇備考：
・商流：元請（弊社）直
・支払いサイト：40日
・商流制限：貴社所属（社員）まで
・備考：個人、フリーランス、外国籍の方は不可となります。正社員の場合は、一定の入社歴がある方を優先いたします。"""

body = json.dumps({
    'destination': 'test',
    'events': [{
        'type': 'message',
        'message': {'type': 'text', 'id': '2', 'text': text},
        'timestamp': 1715676000000,
        'source': {'type': 'user', 'userId': 'U123test'},
        'replyToken': 'test-reply-token-99999',
        'mode': 'active'
    }]
}, ensure_ascii=False)
body_bytes = body.encode('utf-8')
sig = base64.b64encode(hmac.new(secret.encode(), body_bytes, hashlib.sha256).digest()).decode()
res = requests.post(
    'https://ses-work-automation-production.up.railway.app/webhook',
    headers={'Content-Type': 'application/json', 'X-Line-Signature': sig},
    data=body_bytes, timeout=30
)
print(f'status: {res.status_code}')
print(f'body: {res.text[:500]}')
