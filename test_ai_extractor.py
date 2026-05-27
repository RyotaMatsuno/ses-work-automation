
import os, sys

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
sys.path.insert(0, os.path.join(base, "mail_attachment_importer"))
sys.path.insert(0, os.path.join(base, "config"))

os.chdir(base)

# .envロード
from dotenv import dotenv_values
env = dotenv_values(os.path.join(base, "config", ".env"))
for k, v in env.items():
    os.environ[k] = v

# ai_extractor でテキストからエンジニア抽出テスト
from ai_extractor import extract_engineers

test_text = """
氏名：田中 太郎
スキル：Java, Spring Boot, AWS, PostgreSQL
単価：65万円
稼働開始：即日
経験年数：5年
居住地：東京都
"""

print("Testing extract_engineers...")
result = extract_engineers(test_text, "line_test")
print("Result:", result)
