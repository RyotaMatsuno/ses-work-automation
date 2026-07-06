env_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"

with open(env_path, "a", encoding="utf-8") as f:
    f.write(
        "\nOPENAI_API_KEY=REDACTED_API_KEY\n"
    )
    f.write("GEMINI_API_KEY=REDACTED_API_KEY\n")

# 確認
from dotenv import dotenv_values

cfg = dotenv_values(env_path)
print("OPENAI_API_KEY:", "OK" if cfg.get("OPENAI_API_KEY", "").startswith("sk-") else "NG")
print("GEMINI_API_KEY:", "OK" if cfg.get("GEMINI_API_KEY", "").startswith("AIza") else "NG")
