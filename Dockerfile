FROM python:3.12-slim

WORKDIR /app

COPY line_webhook/requirements.txt ./line_webhook/requirements.txt
RUN pip install --no-cache-dir -r line_webhook/requirements.txt \
    gspread google-auth google-auth-oauthlib google-auth-httplib2 python-dateutil

COPY line_webhook/*.py ./line_webhook/
COPY freee/ ./freee/
COPY shibusawa/ ./shibusawa/
COPY sheets/ ./sheets/
COPY common/ ./common/
COPY freee_auth/ ./freee_auth/
COPY sheets_reader.py ./
COPY config/ ./config/

WORKDIR /app/line_webhook
ENV PYTHONPATH=/app:/app/freee_auth

CMD exec gunicorn webhook_server:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --error-logfile -
