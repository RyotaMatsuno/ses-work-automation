# 【Cursor作業指示】タスク4: ドキュメント変数名修正

対象: ses_work/ 以下のCLAUDE.md / SPEC.md / README.md
優先度: P2
根拠: CLAUDE.md等に COST_DAILY_LIMIT / COST_MONTHLY_LIMIT の記載があるが
      ledger.pyが実際に読む変数名は COST_GUARD_DAILY_USD / COST_GUARD_MONTHLY_USD。
      誤名で.envを設定するとデフォルト$1/$6に転落する地雷。

## 修正（PowerShellで実行）
```powershell
$root = "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
Get-ChildItem -Path $root -Include "CLAUDE.md","SPEC.md","README.md" -Recurse | ForEach-Object {
    $c = Get-Content $_.FullName -Raw -Encoding UTF8
    if ($c -match "COST_DAILY_LIMIT|COST_MONTHLY_LIMIT") {
        $c = $c -replace "COST_DAILY_LIMIT", "COST_GUARD_DAILY_USD"
        $c = $c -replace "COST_MONTHLY_LIMIT", "COST_GUARD_MONTHLY_USD"
        Set-Content $_.FullName $c -Encoding UTF8 -NoNewline
        Write-Host "修正: $($_.FullName)"
    }
}
```

## 完了確認
```powershell
Select-String -Path "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\**\CLAUDE.md" -Pattern "COST_DAILY_LIMIT|COST_MONTHLY_LIMIT" -Recurse
```
何も出なければOK。


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
