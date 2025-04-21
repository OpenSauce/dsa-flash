FROM python:3.11-slim
WORKDIR /usr/src/app/app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ../
RUN pip install --no-cache-dir -r ../requirements.txt

COPY . ../

# Run Alembic migrations from root
WORKDIR /usr/src/app
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
