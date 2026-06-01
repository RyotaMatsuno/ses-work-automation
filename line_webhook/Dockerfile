FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webhook_server.py .
COPY remote_command_handler.py .
COPY matching_logic.py .
COPY line_query.py .

CMD exec gunicorn webhook_server:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --error-logfile -
