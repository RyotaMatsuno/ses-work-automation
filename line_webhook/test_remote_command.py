# -*- coding: utf-8 -*-
import os
import sys

from dotenv import dotenv_values

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "config", ".env")
config = dotenv_values(ENV_PATH)

if not (os.environ.get("JOBZ_COMMAND_URL") or config.get("JOBZ_COMMAND_URL")):
    os.environ["JOBZ_COMMAND_URL"] = "http://127.0.0.1:8765"

from remote_command_handler import get_health  # noqa: E402

if __name__ == "__main__":
    print(get_health())
