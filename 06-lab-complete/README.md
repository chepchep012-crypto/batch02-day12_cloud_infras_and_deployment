# Lab 12 — Travel Chatbot (Production + CI/CD)

Production-hoá **AI Travel Chatbot** (Day 5-6 Hackathon) và deploy lên **Railway bằng Docker**,
kèm pipeline **CI/CD GitHub Actions** (lint + unit test coverage → auto deploy).

## 🌍 Live Demo (Railway)

- API: **https://travel-chatbot-production-0b51.up.railway.app**
- Health: [`/health`](https://travel-chatbot-production-0b51.up.railway.app/health)
- Swagger: [`/docs`](https://travel-chatbot-production-0b51.up.railway.app/docs)

```bash
# Chat (rule-based, không cần API key)
curl -X POST https://travel-chatbot-production-0b51.up.railway.app/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

---

## Cấu trúc

```
06-lab-complete/
├── app/
│   ├── main.py            # FastAPI: /health, /ready, /api/chat + JSON logging, CORS, SIGTERM
│   ├── config.py          # 12-factor config từ env
│   ├── routers/chat.py     # POST /api/chat/
│   └── services/chatbot.py # OpenAI + rule-based fallback
├── tests/                 # pytest (14 tests, coverage 93%)
├── Dockerfile             # multi-stage, non-root, healthcheck (~248 MB)
├── docker-compose.yml
├── railway.toml           # builder = DOCKERFILE
├── render.yaml            # Blueprint cho Render (tùy chọn)
├── requirements.txt / requirements-dev.txt
├── pyproject.toml         # cấu hình ruff + pytest + coverage
└── .dockerignore / .env.example
```

CI/CD workflow: [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml)

---

## Chạy local

```bash
# Docker
docker build -t travel-chatbot .
docker run -p 8000:8000 -e PORT=8000 travel-chatbot
curl localhost:8000/health

# Hoặc compose
docker compose up --build
```

## Test + Lint (giống CI)

```bash
pip install -r requirements-dev.txt
ruff check .
pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

---

## CI/CD Pipeline (GitHub Actions)

Trigger: push / PR vào `main` có thay đổi trong `06-lab-complete/`.

| Job | Việc làm |
|-----|----------|
| **CI** | `ruff check` (lint) → `pytest --cov` (unit test, fail nếu coverage < 70%) → upload `coverage.xml` |
| **CD** | Cài Railway CLI → `railway up` (Docker build trên Railway). Chỉ chạy khi push vào `main`. |

### Bật auto-deploy (CD)

CD job sẽ **skip** nếu chưa có token. Để bật:

1. Railway Dashboard → project `day12` → **Settings → Tokens** → tạo **Project Token**.
2. GitHub repo → **Settings → Secrets and variables → Actions**:
   - **Secret** `RAILWAY_TOKEN` = project token vừa tạo.
   - **Variable** `RAILWAY_SERVICE` = `travel-chatbot` (tùy chọn, đã có default).
3. Push lên `main` → pipeline tự build & deploy.

---

## Deploy thủ công (Railway CLI)

```bash
railway link -p <project-id> -e production
railway add -s travel-chatbot
railway up -s travel-chatbot -c -y
railway domain -s travel-chatbot
```
