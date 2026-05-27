# SPEC_collect_v2.md — FALLBACKドメイン差し替え

## 変更目的
collect_targets.pyのFALLBACK_DOMAINSに設定されているダミードメインを
実在するSES・IT企業のドメインに差し替える。

## 差し替えるFALLBACKドメイン（実在する企業のみ）

### SES企業カテゴリ
- https://www.techbrain.co.jp（テックブレーン）
- https://www.mst-inc.co.jp（MST）
- https://www.brainets.co.jp（ブレインズ）
- https://www.isg.co.jp（ISG）
- https://www.fsi.co.jp（富士ソフト子会社）

### SIer・受託開発カテゴリ
- https://www.nsw.co.jp（NSW）
- https://www.tis.co.jp（TIS）
- https://www.nttdata.co.jp（NTTデータ）
- https://www.hitachi-solutions.co.jp（日立ソリューションズ）

## 変更箇所
collect_targets.pyのFALLBACK_DOMAINS変数とKNOWN_COMPANY_NAMES変数を上記内容で差し替える

## 完了条件
- py_compile collect_targets.py エラーなし
- python collect_targets.py --dry-run で新ドメインへのアクセスを試みること（404が出ても可）
