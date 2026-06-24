from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
GEMINI_KEY = config.get("GEMINI_API_KEY") or config.get("GOOGLE_API_KEY")

if not GEMINI_KEY:
    # list all keys that might be relevant
    for k in config:
        if "GEMINI" in k.upper() or "GOOGLE" in k.upper() or "GEM" in k.upper():
            print(f"Found key: {k}")
    print("No Gemini key found, available keys:")
    for k in config:
        print(f"  {k}")
else:
    print(f"Key found: {GEMINI_KEY[:10]}...")
