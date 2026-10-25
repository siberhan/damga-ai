# Live demo image (Cloud Run). Runs in AI_MODE=precomputed with no keys:
# no paid AI calls and no Sepolia transactions. The state resets on every restart.

# 1. Build the React app
FROM node:22-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# 2. Install the ZK script dependencies (snarkjs, circomlibjs)
FROM node:22-slim AS zkdeps
WORKDIR /app/zk
COPY zk/package.json zk/package-lock.json ./
RUN npm ci --omit=dev

# 3. Python backend + Node for the ZK scripts
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY sectors/ sectors/
COPY data/ data/
COPY contracts/abi/ contracts/abi/
COPY contracts/deployments.sepolia.json contracts/
COPY zk/ zk/
COPY --from=zkdeps /app/zk/node_modules zk/node_modules
COPY --from=web /app/web/dist web/dist
ENV AI_MODE=precomputed PYTHONUNBUFFERED=1
WORKDIR /app/backend
CMD exec uvicorn damga.api:app --host 0.0.0.0 --port ${PORT:-8080}
