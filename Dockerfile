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
    postfix postfix-ldap \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Postfix configuration files
COPY backend/postfix/main.cf /etc/postfix/main.cf

COPY backend/app/ ./app/
COPY backend/entrypoint.sh ./entrypoint.sh
COPY --from=frontend-build /app/dist ./static/

CMD ["./entrypoint.sh"]
