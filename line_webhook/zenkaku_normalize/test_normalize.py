import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "line_webhook")
from line_query import normalize_number

cases = [
    ("１０", "10"),
    ("⑮", "15"),
    ("①", "1"),
    ("５", "5"),
    ("10", "10"),
    ("1", "1"),
]

for inp, expected in cases:
    result = normalize_number(inp)
    status = "✅" if result == expected else "❌"
    print(f'{status} normalize_number("{inp}") = "{result}" (expected "{expected}")')
