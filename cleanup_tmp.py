import os, glob
base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
for f in glob.glob(os.path.join(base, "tmp_*.py")):
    os.remove(f)
    print(f"deleted: {os.path.basename(f)}")
print("done")
