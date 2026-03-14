# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# Stage 2: Backend + static files
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential gcc \
    libldap2-dev libsasl2-dev ldap-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/
COPY --from=frontend-build /app/dist ./static/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
