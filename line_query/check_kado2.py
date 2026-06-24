import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

# 稼働可能日・稼働状況 が正しく入っているか
target_correct = "\u7a3c\u5c3d\u53ef\u80fd\u65e5"  # 稼働可能日 <- これが正しいか確認
target_notion = bytes.fromhex("e7a8bce5838de58fafe883bde697a5").decode("utf-8")

sys.stdout.buffer.write(
    f"target_correct: {target_correct!r}  hex={target_correct.encode('utf-8').hex()}\n".encode("utf-8")
)
sys.stdout.buffer.write(
    f"target_notion:  {target_notion!r}   hex={target_notion.encode('utf-8').hex()}\n".encode("utf-8")
)

# 稼働状況
t2_correct = "\u7a3c\u5c3d\u72b6\u6cc1"
t2_notion = bytes.fromhex("e7a8bce5838de78ab6e6b381").decode("utf-8")
sys.stdout.buffer.write(f"t2_correct: {t2_correct!r}  hex={t2_correct.encode('utf-8').hex()}\n".encode("utf-8"))
sys.stdout.buffer.write(f"t2_notion:  {t2_notion!r}   hex={t2_notion.encode('utf-8').hex()}\n".encode("utf-8"))

# ファイルに入っているか
sys.stdout.buffer.write(f"稼働可能日 in file: {(target_notion in text)}\n".encode("utf-8"))
sys.stdout.buffer.write(f"稼働状況 in file: {(t2_notion in text)}\n".encode("utf-8"))
