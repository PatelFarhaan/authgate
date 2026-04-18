# ── Production image ────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

COPY admin/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY admin/ ./admin/

RUN addgroup --system authgate \
    && adduser --system --ingroup authgate authgate \
    && chown -R authgate:authgate /app

USER authgate

EXPOSE 8001

CMD ["uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8001"]
