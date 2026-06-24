# 分類精度改善 GPT-5.4分析結果
Date: 2026-06-23
Benchmark: 280件

{
  "total": 280,
  "match_rate": 0.6464285714285715,
  "cross_table": {
    "project->project": 92,
    "project->other": 7,
    "project->engineer": 14,
    "project->unknown": 7,
    "skip->engineer": 68,
    "skip->other": 1,
    "skip->project": 10,
    "skip->unknown": 1,
    "other->project": 29,
    "other->engineer": 30,
    "other->other": 1,
    "engineer->engineer": 20
  },
  "mismatch_patterns": {
    "project→other": {
      "count": 7,
      "examples": [
        "★注力案件［元請直｜7/1〜｜日本国籍限定リモート］データ連携基盤の官公庁ロビイング・トップライン営業支援募集",
        "0709【Astro?案件】▼50〜70万／PG▼・Windowsバッチ・詳細設計〜改修・＠高田馬場（テレワーク併用可）",
        "Webマーケティング案件/7月～/リモート併用",
        "【BTM案件】【AI】【高田馬場※リモート併用】【MAX75万】（7月or8月：生命保険会社での社員代替支援（AIを活用したWeb開発プロジェクト）)",
        "0711【Astro?案件】▼＊80〜max120万▼・Oracle EBS（DBエンジニア）・上流〜移行・＠江東区（テレワーク併用可）"
      ]
    },
    "project→engineer": {
      "count": 14,
      "examples": [
        "【直フリーランス】Webデザイナー（未経験可）／HTML・CSS・Figma／即日～／飲食・サービス・小売",
        "※新規営業! ★常駐OK! 【人材ー React・Vue・TypeScript / フロントSE / 要件定義から一貫して対応可! / リーダー経験あり! 】O.K @青戸駅 / 55万 / 7月～【サクヤ 吉田】★",
        "【フロントエンド】Vue.js・Nuxt3・React実動。TypeScript/JavaScript/Docker【 常駐可能 /7月～】 | Tech4U",
        "【ダイバージェンス社員】Microsoft365 / M365 / Active Directory / 運用保守 / ヘルプデスク / 即日",
        "【8月人材】CCNA | ネットワーク詳細設計・構築〜 | 常駐可"
      ]
    },
    "project→unknown": {
      "count": 7,
      "examples": [
        "【7月～外国籍可】JavaScript,HTML,CSS3年～／大手キャッシュレス決済におけるフロントエンドエンジニア",
        "【ARI】大手損害保険会社向け クラウドモダナイゼーション推進支援 ",
        "上位同席1回,フルリモ///AWS,ネットワーク,Lambda",
        "上位同席1回,Winサーバ設計構築///品川,週1テレ",
        "【ARI】製薬会社向け データ利活用基盤（モダンデータスタック）拡張・改修／Snowflakeエンジニア"
      ]
    },
    "skip→other": {
      "count": 1,
      "examples": [
        "AI時代、企業のIT・人材戦略の最適解は？─AI経営・DXのトップランナーが語る（WorksWay 2026）"
      ]
    },
    "skip→project": {
      "count": 10,
      "examples": [
        "★【システム移行計画の策定経験｜〜144万円｜リモート併用】＿WhiteBox",
        "★【元請け直 / Java(SpringBoot) ・AWS / 75～85万】生命保険会社向けWebシステム開発 / 7月～長期 ＠汐留or都内近郊【サクヤ 瀧澤】★",
        "データエンジニア案件/〜75万/HR系/SQL/Databricks/Redshift/BigQuery/7月〜/＠大手町駅or五反田駅※基本リモート【レルモ櫻井】",
        "★【プリセールス × GCS｜コミュ力 × NW設計構築｜飯田橋リモート併用｜〜128万】＿WhiteBox",
        "【注力案件】＜即日/リモート併用（大崎駅）/SE＞生成AIパッケージのインフラ要員《Azure、Terraform、AI関連サービスほか》"
      ]
    },
    "skip→unknown": {
      "count": 1,
      "examples": [
        "Microsoft CEOが語った「AI時代に、企業が手放せないもの」とは"
      ]
    },
    "other→project": {
      "count": 29,
      "examples": [
        "※最注力案件　5件　【アイエンター鈴木】",
        "【単価下がりました！日本語流暢です！Java案件ください！】即日〜弊社プロパー/Java・Spring Boot ・COBOL ・JavaScript・Vue.js・HTML・CSS ・MySQL・PostgreSQL・IBM Db2 ・J",
        "NW案件/〜110万/Azure・AWS・DCAWS/企画・設計・構築/8月〜/＠大手町駅※リモート併用【レルモ櫻井】",
        "【GFD案件】インフラ/7月～/NW設計/リーダー経験者募集/Cisco/FortiGate/Palo Alto/PMO",
        "【弊社BPが別PJに2名参画中】7月or8月〜/NW設計構築2年上の経験必須/リモート比率高め"
      ]
    },
    "other→engineer": {
      "count": 30,
      "examples": [
        "【直フリーランス】動画編集・SNS運用／ディレクション・広報支援／即日～／官公庁・美容・メディア",
        "【SasaTech 人材】【即日〜95万】【Androidリード / フルスタック対応】AI駆動で大規模開発を加速させるエンジニアのご紹介",
        "【SasaTech 人材】【5/1〜55万】【Windows Server 2022 / IIS 10.0】PowerShellでの自動化もこなす構築・運用エンジニア",
        "【SasaTech 人材】【7月〜65万〜70万】【TypeScript / JavaScript】業界歴10年以上！フロントエンド実装からディレクションまで一気通貫でこなすSE",
        "【BTM人材】当社1社下正社員YO 34歳（4月：Python, SQL, JavaScript, VBA, Linux, Windows）"
      ]
    }
  }
}