import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import line_query

importlib.reload(line_query)
from line_query import engineer_query

result = engineer_query("HS", "\u5317\u5c0f\u91d1")
sys.stdout.buffer.write(result.encode("utf-8"))
sys.stdout.buffer.write(b"\n")
