FROM python:3.12-slim

WORKDIR /app

# Build context must be the parent ses_work/ directory:
#   gcloud builds submit --config line_webhook/Dockerfile ..
#   or: docker build -f line_webhook/Dockerfile ..
COPY line_webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Webhook application files
COPY line_webhook/webhook_server.py .
COPY line_webhook/remote_command_handler.py .
COPY line_webhook/matching_logic.py .
COPY line_webhook/line_query.py .
COPY line_webhook/line_bridge.py .
COPY line_webhook/skill_extractor.py .
COPY line_webhook/skill_utils.py .

# Global cost guard (cost_guard_v2)
COPY cost_guard.py .
COPY common/ common/
COPY config/model_rates.json config/model_rates.json
COPY config/dedup_target_required.json config/dedup_target_required.json

CMD exec gunicorn webhook_server:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --access-logfile - --error-logfile -
