FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "trippilot.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src", "--reload"]
