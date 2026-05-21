
import base64
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx", "rb") as f:
    data = base64.b64encode(f.read()).decode()
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\excel_b64.txt", "w") as f:
    f.write(data)
print(f"done: {len(data)} chars")
