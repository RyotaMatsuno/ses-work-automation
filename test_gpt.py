import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
sys.path.insert(0, str(base / "matching_v3"))
sys.path.insert(0, str(base))

from structurer import structurize

from config import Config

cfg = Config()
print(f"モデル: {cfg.structurer_model}")

# テストメール（案件）
test_mail = """
件名: 【案件】Javaバックエンド開発者募集

業務内容: ECサイトのバックエンドAPI開発・保守
必須スキル: Java, Spring Boot, SQL
尚可スキル: AWS, Docker
単価: 60〜65万円
期間: 2026年7月〜長期
勤務地: 東京（リモート可）
面談: 1回
"""

print("GPT API呼び出しテスト中...")
result = structurize(test_mail, cfg)
print("\n結果:")
import json

print(json.dumps(result, ensure_ascii=False, indent=2))
