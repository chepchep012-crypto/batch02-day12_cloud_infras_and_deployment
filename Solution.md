# Solution — Day 12 Lab: Deployment & Cloud Infrastructure

> **AICB-P1 · VinUniversity 2026**
> Học viên: ToanNguyen — Nộp trước 24h ngày 12/06/2026
>
> Gồm 2 phần theo [DAY12_DELIVERY_CHECKLIST.md](DAY12_DELIVERY_CHECKLIST.md):
> 1. **Đáp án codelab Part 1→5** (bên dưới)
> 2. **Project Lab Assignment** — Travel Chatbot productionized + deploy ([Phần cuối](#-project-lab-assignment))

---

## Part 1 — Localhost vs Production

### Exercise 1.1 — Anti-patterns trong `01-localhost-vs-production/develop/app.py`

| # | Anti-pattern | Code | Tại sao nguy hiểm |
|---|--------------|------|-------------------|
| 1 | **Hardcode secret/API key** | `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"`, `DATABASE_URL = "postgresql://admin:password123@..."` | Push lên Git → lộ key/credentials ngay lập tức |
| 2 | **Debug mode bật** | `DEBUG = True` | Lộ stack trace, thông tin nội bộ ra client |
| 3 | **Print thay logging + log cả secret** | `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` | Không structured, không level, và ghi secret ra stdout |
| 4 | **Không có health check** | (thiếu endpoint `/health`) | Agent crash → platform không biết để restart |
| 5 | **Port/host cứng + reload** | `host="localhost", port=8000, reload=True` | Chỉ chạy local, không đọc `PORT` từ env, reload không dùng cho prod |

→ **Giải pháp:** [12-Factor App](https://12factor.net/) — config từ env, logging ra stdout, stateless, port từ env…

### Exercise 1.3 — So sánh `develop` vs `production`

| Feature | Basic (develop) | Advanced (production) | Tại sao quan trọng |
|---------|-----------------|------------------------|--------------------|
| **Config** | Hardcode trong code | `os.getenv(...)` qua `config.py`, có validate | Đổi config không cần sửa code; không lộ secret |
| **Health check** | ❌ Không có | ✅ `/health` (liveness) + `/ready` (readiness) | Platform tự restart / điều phối traffic |
| **Logging** | `print()` | JSON structured: `{"time":..,"level":..,"msg":..}` | Máy đọc được, đẩy lên log aggregator, không log secret |
| **Shutdown** | Đột ngột (`reload=True`, không hook) | Graceful: `lifespan` + `signal.SIGTERM`, chờ request xong | Không rớt request đang xử lý khi deploy/restart |
| **Host/Port** | `localhost:8000` cứng | `0.0.0.0` + `PORT` từ env | Chạy được trong container/cloud |

---

## Part 2 — Docker Containerization

### Exercise 2.1 — `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11` (full, ~1 GB).
2. **WORKDIR:** `/app`.
3. **Tại sao COPY `requirements.txt` trước code:** tận dụng **layer caching** — nếu chỉ code đổi mà dependencies không đổi, Docker dùng lại layer `pip install` đã cache → build nhanh hơn nhiều.
4. **CMD:** `CMD ["python", "app.py"]` (exec form). Không có `ENTRYPOINT`.
   - **CMD vs ENTRYPOINT:** `ENTRYPOINT` = lệnh cố định luôn chạy; `CMD` = lệnh/tham số **mặc định**, dễ bị override khi `docker run <image> <cmd>`. Pattern phổ biến: `ENTRYPOINT` cho binary, `CMD` cho tham số mặc định.

### Exercise 2.3 — Multi-stage (`02-docker/production/Dockerfile`)

- **Stage 1 (builder):** cài build tools (`gcc`, `libpq-dev`), `pip install --user` vào `/root/.local`. Stage này **không** đi vào image cuối.
- **Stage 2 (runtime):** base `python:3.11-slim`, tạo **non-root user** `appuser`, chỉ `COPY --from=builder /root/.local ...` (chỉ package runtime) + source code, `USER appuser`, có `HEALTHCHECK`.
- **Tại sao nhỏ hơn:** image cuối không có gcc/headers/apt cache; dùng `-slim` (~150 MB thay vì ~1 GB) → an toàn & nhẹ hơn.
- **CMD:** `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2`.

### Exercise 2.4 — Docker Compose stack (`02-docker/production`)

Services: **agent** (FastAPI) · **redis** (cache/session) · **qdrant** (vector DB) · **nginx** (reverse proxy + LB).

```
Client ──▶ nginx (:80/:443) ──▶ agent:8000 ──┬─▶ redis:6379
                                              └─▶ qdrant:6333
```

- **Communicate:** chung network bridge `internal`; agent gọi service qua DNS tên service (`redis://redis:6379`, `http://qdrant:6333`).
- **depends_on … condition: service_healthy:** agent chỉ start khi redis & qdrant healthy.
- **Ports:** chỉ nginx expose ra ngoài (80/443); agent/redis/qdrant chỉ internal. `nginx.conf` có `upstream agent_backend`, rate-limit `10r/s`, security headers, custom 429.

---

## Part 3 — Cloud Deployment

### Exercise 3.2 — `railway.toml` vs `render.yaml`

| Khía cạnh | railway.toml | render.yaml |
|-----------|--------------|-------------|
| **Builder** | `NIXPACKS` (auto-detect Python) | `runtime: python` + `buildCommand` |
| **Start command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` | giống hệt |
| **Health check** | `healthcheckPath="/health"`, `healthcheckTimeout=30` | `healthCheckPath: /health` |
| **Env vars** | set qua CLI/Dashboard | khai báo trong `envVars`: `sync:false` (thủ công) hoặc `generateValue:true` (tự sinh) |
| **Auto-deploy** | (không khai báo trong toml) | `autoDeploy: true` (deploy khi push GitHub) |
| **Restart policy** | `ON_FAILURE`, max 3 retries | (không khai báo) |
| **Cú pháp** | TOML, section `[build]`/`[deploy]` | YAML, mảng `services` (mở rộng nhiều service dễ) |

### Exercise 3.3 — Cloud Run CI/CD (`cloudbuild.yaml` + `service.yaml`)

**`cloudbuild.yaml` (pipeline 4 bước, trigger khi push `main`):**
1. **Test** — `pytest tests/` (fail là dừng pipeline).
2. **Build** — `docker build` tag `$COMMIT_SHA` + `latest`, dùng `--cache-from`.
3. **Push** — đẩy lên Google Container Registry.
4. **Deploy** — `gcloud run deploy` region `asia-southeast1`, `--allow-unauthenticated`.

**`service.yaml`:** minScale 1 / maxScale 10, `containerConcurrency: 80`, CPU 0.5–1 / RAM 256–512Mi, port 8000, timeout 60s, liveness `/health` + startup probe `/ready`, secrets từ Secret Manager.

---

## Part 4 — API Security

### Exercise 4.1 — API Key auth (`develop/app.py`)

- Header **`X-API-Key`**, kiểm trong dependency `verify_api_key()` (so với env `AGENT_API_KEY`).
- **Thiếu key → 401**; **sai key → 403**.
- **Rotate key:** đổi biến môi trường `AGENT_API_KEY` rồi restart (không sửa code).

### Exercise 4.2 — JWT (`production/auth.py`)

- **Lấy token:** `POST /auth/token` với `username`+`password` → `authenticate_user()` → `create_token()`.
- **Payload:** `sub` (user), `role`, `iat`, `exp` (+60 phút).
- **Verify:** header `Authorization: Bearer <token>` → `jwt.decode(token, SECRET_KEY, algorithms=["HS256"])`.
- **Config:** secret `JWT_SECRET`, algorithm `HS256`, expiry `60` phút.

### Exercise 4.3 — Rate limiting (`production/rate_limiter.py`)

- **Thuật toán:** **Sliding Window Counter** (deque timestamp mỗi user, loại bỏ timestamp ngoài cửa sổ 60s).
- **Limit:** user `10 req/phút`, **admin `100 req/phút`** (bypass theo role: `limiter = rate_limiter_admin if role=="admin" else rate_limiter_user`).
- **Lưu state:** in-memory `defaultdict(deque)`.
- **Vượt → 429** kèm header `X-RateLimit-*`, `Retry-After`.

### Exercise 4.4 — Cost guard (`production/cost_guard.py`)

- Track theo `UsageRecord` mỗi user/ngày (input/output tokens, request_count); cost = `tokens/1000 * giá` (GPT-4o-mini: `$0.00015/1K in`, `$0.0006/1K out`).
- **Budget:** user `$1/ngày`, global `$10/ngày`; cảnh báo tại 80%.
- **Vượt:** user → **402 Payment Required**; global → **503**.
- **Reset:** mỗi ngày (so `record.day != today`). Demo lưu in-memory (production nên dùng Redis — xem solution trong CODE_LAB).

---

## Part 5 — Scaling & Reliability

### Exercise 5.1 — Health vs Readiness

- **`/health` (liveness):** "process còn sống?" — check memory (`psutil`), trả `ok`/`degraded`. Không phụ thuộc dependency.
- **`/ready` (readiness):** "sẵn sàng nhận traffic?" — **ping Redis**, nếu Redis down → **503** (load balancer ngừng route vào).

### Exercise 5.2 — Graceful shutdown

- Bắt `SIGTERM`/`SIGINT` qua `signal.signal()`; uvicorn `timeout_graceful_shutdown=30`.
- `lifespan`: shutdown set `_is_ready=False`, **drain** — chờ tới 30s cho các in-flight request (đếm qua middleware) hoàn thành rồi mới thoát.

### Exercise 5.3 — Stateless design

- **develop:** state in-memory `_memory_store = {}` → "not scalable".
- **production:** lưu vào **Redis** — `save_session()` dùng `setex(f"session:{id}", ttl, data)`, `append_to_history()` cap 20 message. Mỗi instance đọc/ghi cùng Redis → **instance-agnostic**; response trả `served_by = INSTANCE_ID` để chứng minh.

### Exercise 5.4 — Load balancing

- `docker-compose.yml`: agent `deploy.replicas: 3`, mỗi instance limit 0.5 CPU/256M, healthcheck 15s.
- `nginx.conf`: `upstream agent_cluster { server agent:8000; keepalive 16; }` — Docker DNS `agent` phân giải ra cả 3 container, Nginx **round-robin** mặc định; `proxy_next_upstream error timeout http_503` retry tối đa 3 lần; header `X-Served-By $upstream_addr`.

### Exercise 5.5 — `test_stateless.py`

1. Gửi 5 câu hỏi liên tiếp qua `POST /chat`, request đầu tạo `session_id`, các request sau truyền lại `session_id`.
2. Thu thập `served_by` → tập `instances_seen` (chứng minh nhiều instance phục vụ).
3. `GET /chat/{session_id}/history` → kiểm tra đủ **10 message** (5 Q + 5 A) dù request rải qua nhiều instance → **state sống sót** nhờ Redis.

---

## 🚀 Project Lab Assignment

> **Yêu cầu:** thay project trong `06-lab-complete` bằng dự án cá nhân (1 agent từ buổi trước), restructure theo các bước productionization, deploy và note API URL.

### Dự án: **AI Travel Chatbot** (Day 5-6 Hackathon)

FastAPI chatbot tư vấn du lịch (OpenAI GPT-3.5 + rule-based fallback offline), đã được **production-hoá** và đưa vào [06-lab-complete/](06-lab-complete/).

### 🔗 API URL (LIVE trên Railway)

**https://travel-chatbot-production-0b51.up.railway.app**

| Endpoint | Mô tả |
|----------|-------|
| [`GET /health`](https://travel-chatbot-production-0b51.up.railway.app/health) | Liveness probe |
| [`GET /ready`](https://travel-chatbot-production-0b51.up.railway.app/ready) | Readiness probe |
| `POST /api/chat/` | Chat (body: `{"messages":[{"role":"user","content":"hello"}]}`) |
| [`GET /docs`](https://travel-chatbot-production-0b51.up.railway.app/docs) | Swagger UI |

```bash
curl -X POST https://travel-chatbot-production-0b51.up.railway.app/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Cho tôi thông tin về Hà Nội"}]}'
```

### Các bước productionization đã áp dụng

| Bước | Áp dụng |
|------|---------|
| 12-Factor config | `app/config.py` đọc toàn bộ từ env (PORT, OPENAI_API_KEY, CORS_ORIGINS, LOG_LEVEL…) |
| Structured logging | JSON log + observability middleware (method/path/status/ms) |
| Health/Readiness | `/health` + `/ready` (lifespan set `_is_ready`) |
| Graceful shutdown | handler `SIGTERM` |
| Security | CORS, security headers (`X-Content-Type-Options`, `X-Frame-Options`) |
| Docker | **Multi-stage**, non-root user, `HEALTHCHECK`, image **~248 MB** (< 500MB) |
| Deploy | Railway qua **Docker** (`railway.toml` builder=DOCKERFILE) |

### Bonus — CI/CD GitHub Actions ✅

[.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml) — đã chạy **thành công** ([run log](https://github.com/chepchep012-crypto/batch02-day12_cloud_infras_and_deployment/actions)):

- **CI:** `ruff check` (lint) → `pytest --cov` (**14 tests, coverage 93%**, fail nếu < 70%) → upload `coverage.xml`.
- **CD:** Railway CLI → `railway up` (Docker build trên Railway) khi push `main`.

### Cấu trúc & cách chạy

```
06-lab-complete/
├── app/{main,config}.py · routers/chat.py · services/chatbot.py
├── tests/                 # 14 unit tests, coverage 93%
├── Dockerfile · docker-compose.yml · railway.toml · render.yaml
├── requirements.txt · requirements-dev.txt · pyproject.toml
└── .dockerignore · .env.example
```

```bash
# Local
cd 06-lab-complete
docker build -t travel-chatbot . && docker run -p 8000:8000 -e PORT=8000 travel-chatbot
# Test + lint (giống CI)
pip install -r requirements-dev.txt && ruff check . && pytest --cov=app --cov-fail-under=70
```

Chi tiết: [06-lab-complete/README.md](06-lab-complete/README.md).
