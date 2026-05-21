import os
from dotenv import dotenv_values
config = dotenv_values('config/.env')
for k,v in config.items():
    if k not in os.environ:
        os.environ[k] = v

import anthropic
c = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
models = c.models.list()
for m in models.data[:8]:
    print(m.id)
