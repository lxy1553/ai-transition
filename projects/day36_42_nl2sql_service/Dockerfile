FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY projects /app/projects

ENV PYTHONPATH=/app/projects/day36_42_nl2sql_service
ENV APP_ENV=container

EXPOSE 8000

CMD ["uvicorn", "projects.day36_42_nl2sql_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

