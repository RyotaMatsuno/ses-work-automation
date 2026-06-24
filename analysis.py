import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# GPT/Gemini 3視点分析 → ジョブズ統合設計
print("""
=== GPT-o3視点（速度・シンプルさ） ===
問題: テキストベースのスキルシート送信時、line_queryがNoneを返した後
     classify_messageが「engineer」と判定して「スキルシートを送ってください」を返す。
     これはフローとして正しいが、ユーザー体験が悪い。
     
修正案: classify_messageがengineer判定 + テキストが100文字以上の場合は
        直接Notionに登録してマッチングを返す。
        （50文字ガードはline_queryへの入力として適切、classify_messageは別ルート）

=== Gemini視点（アーキテクチャ・長期保守） ===
問題の本質は「受信パス」が2つある:
  1. line_queryルート（短いコマンド → 照会結果返却）
  2. classify_messageルート（長いテキスト → DB登録・マッチング）

現状: line_queryがNoneを返した後にclassify_messageが走る。
     engineer判定 → 「ファイルを送ってください」（スキルシート待機）
     
しかしスキルシート本文テキスト（100文字以上のengineer情報）は
直接登録できるはず。ファイル送付を強制する必要はない。

修正案: classify_messageがengineer + テキスト100文字以上 → 直接登録ルート
        classify_messageがengineer + テキスト100文字未満 → ファイル待機ルート

=== ジョブズ判断（ROI・実装コスト・緊急度） ===
松野の状況:
- 「HS 北小金」というLINE照会クエリを送っても動かない
- スキルシートテキストを送ったら「ファイルを送ってください」と返ってくる
- H.SのNotionレコードにイニシャル・最寄り駅が空

優先修正順:
1. 【最優先】H.SのNotionレコードにイニシャル(HS)・最寄り駅(北小金)を正しく登録
2. 【最優先】スキルシートテキストを送ったら直接登録してマッチング結果を返す
3. 【高優先】テキスト登録時にイニシャル・最寄り駅を正しく抽出して保存
4. 【中優先】line_queryのデプロイ確認（Cloud Runに最新版が当たっているか）

実装コスト:
- #1: Notion PATCH 1回 = 簡単
- #2: classify_message engineer → 直接登録ルートに変更 = 中程度
- #3: classify_messageのプロンプトにイニシャル・駅の抽出を追加 = 中程度  
- #4: デプロイ確認 = 簡単

全部やる。
""")

print("=== H.SレコードのPage IDを取得 ===")
