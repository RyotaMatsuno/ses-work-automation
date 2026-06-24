import os

spec = """# SPEC.md - 入力元ラベル・所属会社名 追加

最終更新: 2026-05-26

## 概要
メール・LINEで届いた案件/人材情報に「入力元ラベル」「所属会社名」を付与してNotionに保存。
マッチング結果通知にも表示する。

## 入力元ラベル一覧
| 入力元 | ラベル |
|---|---|
| r-matsuno@ | 松野メール |
| r-okamoto@ | 岡本メール |
| sessales@ | 共通メール |
| 松野LINE（user_id: Ue3508b43b84991f5a68281da5bf4cf39） | 松野LINE |
| 岡本LINE（user_id: Uac1d23408573586affa37577c4e2b2ab） | 岡本LINE |

## 対象ファイル
1. ses_work/mail_pipeline/mail_pipeline.py
2. ses_work/line_webhook/webhook_server.py
3. ses_work/matching_v2/notify_line.py

## 修正1: mail_pipeline.py
- メール受信時にFromアドレスを見てラベルを判定: `get_source_label(from_addr: str) -> str`
- 本文からAIで所属会社名を抽出（取れなければ空欄）
- エンジニアDB・案件DB登録時に `入力元` `所属会社名` フィールドを追記

## 修正2: webhook_server.py
- user_idを見て `松野LINE` / `岡本LINE` ラベルを付与
- Notion登録時に `入力元` フィールドを追記（所属名不要）

## 修正3: notify_line.py
- LINE通知文に `入力元` `所属会社名` を含める
- LINE入力元（松野LINE/岡本LINE）案件には ⚡ を付けて優先表示

## LINE優先度ソート
- LINE経由案件を先頭に表示（⚡マーク付き）
- メール経由は後続

## NotionDBフィールド確認
- エンジニアDB・案件DBに `入力元`（select）`所属会社名`（text）が存在するか確認
- なければ追加（Notion REST APIで）

## 完了条件
1. py_compile mail_pipeline/mail_pipeline.py → エラーなし
2. py_compile line_webhook/webhook_server.py → エラーなし
3. py_compile matching_v2/notify_line.py → エラーなし
4. get_source_label('r-matsuno@terra-ltd.co.jp') → '松野メール'
"""

tasks = """# TASKS.md - 入力元ラベル・所属会社名

- [ ] 1. mail_pipeline.py: get_source_label(from_addr)関数を追加
- [ ] 2. mail_pipeline.py: AI所属会社名抽出をメール本文から実装（取れなければ空欄）
- [ ] 3. mail_pipeline.py: エンジニア/案件Notion登録時に入力元・所属会社名を追記
- [ ] 4. webhook_server.py: user_idでラベル付与（松野LINE/岡本LINE）、Notion登録に入力元追記
- [ ] 5. notify_line.py: LINE通知文に入力元・所属会社名を追加、LINE案件に⚡付けて先頭ソート
- [ ] 6. py_compile 3ファイル確認
- [ ] 7. get_source_label単体テスト（松野メール/岡本メール/共通メールの3ケース）
"""

claude_md = """# CLAUDE.md - 入力元ラベル・所属会社名

## 禁止事項
- 既存の送信ロジックを壊さない（追記のみ）
- Notionフィールドが存在しない場合はスキップ（エラーにしない）
- LINE user_idをログに出力しない

## コーディングルール
- Python 3.11
- エラーは握りつぶさずログに書く
- Notionフィールド追加は行わない（既存フィールドへの書き込みのみ）

## 対象ディレクトリ
- ses_work/mail_pipeline/mail_pipeline.py
- ses_work/line_webhook/webhook_server.py
- ses_work/matching_v2/notify_line.py
"""

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\input_label_spec"
os.makedirs(base, exist_ok=True)
open(os.path.join(base, "SPEC.md"), "w", encoding="utf-8").write(spec)
open(os.path.join(base, "TASKS.md"), "w", encoding="utf-8").write(tasks)
open(os.path.join(base, "CLAUDE.md"), "w", encoding="utf-8").write(claude_md)
print("3点セット作成完了")
