# 【Cursor作業指示】タスク3: orphanファイル削除 + デバッグスクリプトアーカイブ

対象: ses_work/ ルート
優先度: P2

## 削除: orphan cost_state（正本はAppData。これらは使われていない）
```
del "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\common\cost_state.json"
del "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cost_guard_state.json"
```

## アーカイブ: デバッグ用使い捨てスクリプト
```
mkdir "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_archive\debug_scripts_20260615"
move "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_check_*.py" "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_archive\debug_scripts_20260615\"
move "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_wall_*.py" "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_archive\debug_scripts_20260615\"
move "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_raw_*.py" "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_archive\debug_scripts_20260615\"
move "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_audit_*.py" "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_archive\debug_scripts_20260615\"
```

## 完了確認
```
python -c "
from pathlib import Path
for p in [Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\common\cost_state.json'), Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cost_guard_state.json')]:
    print(p.name, '削除済み✅' if not p.exists() else 'まだ存在❌')
"
```


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
