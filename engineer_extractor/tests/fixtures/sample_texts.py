"""Sample engineer texts for testing — 3 patterns + edge cases."""

SAMPLE_AUTO_IMPORT = """\
[自動取込] 件名: 【SasaTech 人材】【7月〜65万（応相談）】【RHEL / CLUSTERPRO / JP1】インフラエンジニア（サーバー構築・運用）
送信元: 株式会社SasaTech SES事業部<ses@sasatech.co.jp>
受信日: Wed, 17 Jun 2026 07:03:13 +0900 (JST)

山田 太郎
40歳/男性
最寄り駅：JR東海道線 横浜駅
業界歴10年以上。Linuxサーバー設計・構築・運用の経験豊富。
スキル：Linux, RHEL, JP1, CLUSTERPRO, Shell, Ansible
稼働可能日：2026年7月1日より
"""

SAMPLE_EMAIL_REGISTER = """\
【メールから自動登録】
送信者: sales@conviction-inc.com
件名: D.E｜蕨駅｜iOS開発11年／Swift・Kotlin・Java／Android・iOS両対応

40歳女性。最寄駅：JR埼京線大宮駅。
開発歴11年。Swift, Kotlin, Java, Objective-Cが得意です。
Android/iOS両対応のアプリ開発経験多数。
単価: 75万（応相談）
稼働可能日：即日
"""

SAMPLE_LINE_REGISTER = """\
[LINE登録: matsuno]
【名前】Y.S（33歳男性）
【単価】40万円(応相談)
【スキル】PHP, Java, SQL, JavaScript, Vue
【最寄】船橋競馬場駅
【開始】7月～
【所属】フリーランス
【備考】フルリモート希望
"""

SAMPLE_LINE_REGISTER_AUTO = """\
[LINE auto-register: jobz]
【名前】T.K（28歳男性）
【単価】55万
【スキル】Python, Django, React, AWS, Docker
【最寄り駅】半蔵門線 錦糸町駅
【開始】即日
"""

SAMPLE_UNKNOWN = """\
田中 花子
SE経験3.5年
スキル：Python, FastAPI, PostgreSQL, Docker, GitHub Actions
最寄り駅：東京メトロ丸ノ内線 新宿駅
単価：50〜60万
稼働可能日：2026/08/01～
"""

SAMPLE_EMPTY = ""

SAMPLE_WHITESPACE = "   \n\t  "
