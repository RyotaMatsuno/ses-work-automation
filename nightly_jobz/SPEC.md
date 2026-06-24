# nightly_jobz

深夜自律処理バッチ（Phase 1 最小構成）。

## 実行

```powershell
cd ses_work
$env:NIGHTLY_DRY_RUN="1"
python -m nightly_jobz.nightly_jobz
```

## スケジューラ登録（23:55）

```powershell
schtasks /Create /TN "SES_NightlyJobz" /TR "python -m nightly_jobz.nightly_jobz" /SC DAILY /ST 23:55 /F
```

作業ディレクトリは `ses_work` を指定すること。

## Phase 1 スコープ

- investigation / spec_design のみ実装
- draft_intent / draft_proposal / matching → blocked
- LINE送信なし
