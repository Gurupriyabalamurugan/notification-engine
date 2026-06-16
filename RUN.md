# Notification Engine — Run Steps

Ordered commands to run the full stack on **Windows (PowerShell)**.

## 1. Clone and enter the project

```powershell
cd C:\Users\lalitsr\Projects\notification-engine
```

---

## 2. Create environment file

```powershell
Copy-Item .env.example .env
```

If you run migrations or the API **locally** (outside Docker), update `.env` to match Docker host ports:

```env
DATABASE_URL=postgresql+asyncpg://notification:notification@localhost:5433/notification_engine
REDIS_URL=redis://localhost:6380/0
KAFKA_BOOTSTRAP_SERVERS=localhost:19092
```

> Inside Docker containers, services use internal hostnames (`postgres`, `redis`, `redpanda`) — no change needed there.

---

## 3. Start the full stack

```powershell
docker compose up -d --build
```

Wait until all services are up:

```powershell
docker compose ps
```

Expected services:

| Service       | Host port | Purpose              |
|---------------|-----------|----------------------|
| api           | 8000      | FastAPI + Swagger    |
| postgres      | 5433      | Database             |
| redis         | 6380      | Idempotency cache    |
| redpanda      | 19092     | Kafka broker         |
| worker        | —         | Dispatcher           |
| retry-worker  | —         | Retry scheduler      |
| init-kafka    | (exits)   | Creates Kafka topics |

---

## 4. Run database migrations (first run only)

**Inside the API container (recommended):**

```powershell
docker compose exec api alembic upgrade head
```

**Or locally** (requires `.env` with port `5433` for Postgres):

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\alembic upgrade head
```

---

## 5. Verify the API is healthy

```powershell
curl.exe http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Open in browser:

- Health: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs

---

## 6. Send a test notification

PowerShell mangles JSON in `curl.exe -d` unless you use **`--%`** (stop-parsing) or `Invoke-RestMethod`.

**Option A — curl with `--%` (recommended for copy-paste):**

```powershell
curl.exe --% -X POST http://localhost:8000/v1/notifications -H "Content-Type: application/json" -H "Idempotency-Key: test-1" -d "{\"idempotency_key\":\"test-1\",\"source_service\":\"payment\",\"event_type\":\"otp\",\"user_id\":\"u1\",\"channels\":[\"sms\"],\"payload\":{\"code\":\"123456\"}}"
```

**Option B — Invoke-RestMethod:**

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/v1/notifications" `
  -ContentType "application/json" `
  -Headers @{ "Idempotency-Key" = "test-1" } `
  -Body '{"idempotency_key":"test-1","source_service":"payment","event_type":"otp","user_id":"u1","channels":["sms"],"payload":{"code":"123456"}}'
```

**Option C — Swagger UI:** http://localhost:8000/docs → `POST /v1/notifications` → **Try it out**

Expected response:

```json
{"notification_id":"...","status":"Pending","created":true}
```

---

## 7. Check notification status

Replace `{notification_id}` with the ID from step 6:

```powershell
curl.exe http://localhost:8000/v1/notifications/{notification_id}
```

Or with `Invoke-RestMethod`:

```powershell
Invoke-RestMethod "http://localhost:8000/v1/notifications/{notification_id}"
```

---

## 8. Seed sample events (optional)

With the API running:

```powershell
.venv\Scripts\python scripts/seed_events.py --base-url http://localhost:8000
```

---

## 9. Run tests (optional)

```powershell
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\pytest -v
```

Integration tests need Postgres on port **5433** (`docker compose up -d postgres` is enough if the full stack is not running).

---

## 10. View logs

```powershell
docker compose logs -f api worker retry-worker
```

Press `Ctrl+C` to stop tailing.

---

## 11. Stop the stack

```powershell
docker compose down
```

Remove volumes (wipes DB data):

```powershell
docker compose down -v
```

---

## Local development (API on host, infra in Docker)

```powershell
Copy-Item .env.example .env
# Set DATABASE_URL port to 5433, REDIS_URL to 6380 (see step 2)

docker compose up -d postgres redis redpanda
docker compose run --rm init-kafka

python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\alembic upgrade head
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

In separate terminals:

```powershell
.venv\Scripts\python -m app.workers.dispatcher_worker
.venv\Scripts\python -m app.workers.retry_worker
```

---


## Quick reference

```powershell
docker compose up -d --build                              # Start everything
docker compose exec api alembic upgrade head              # Migrate
curl.exe http://localhost:8000/health                     # Health check
docker compose logs -f api worker retry-worker            # Logs
docker compose down                                       # Stop
```
