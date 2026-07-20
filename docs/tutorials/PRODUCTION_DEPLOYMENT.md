# Production Deployment Checklist

This guide covers deploying New Gen Agent to production environments.

---

## Pre-deployment checklist

### 1. Code quality

- [ ] All tests pass: `pytest`
- [ ] Coverage ≥ 70%: `pytest --cov=gen_agent`
- [ ] Linter clean: `ruff check gen_agent/ tests/ config/ server/`
- [ ] Type checker clean: `mypy gen_agent/ --ignore-missing-imports`
- [ ] Security audit: `pip-audit` (no known vulnerabilities)
- [ ] Pre-commit hooks installed: `pre-commit install`

### 2. Configuration

- [ ] Environment variables documented (`.env.example`)
- [ ] Secrets stored securely (Vault, AWS Secrets Manager, etc.)
- [ ] Database migrations tested: `alembic upgrade head`
- [ ] LLM provider selected and tested (Ollama/OpenRouter/custom)
- [ ] Log level set appropriately (`LOG_LEVEL=INFO` for prod, `DEBUG` for staging)

### 3. Performance

- [ ] Benchmarks run and recorded (`benchmarks/history.json`)
- [ ] Resource limits defined (CPU, memory, disk)
- [ ] Database connection pool tuned (PostgreSQL: `pool_size`, `max_overflow`)
- [ ] LLM circuit breaker configured (`CIRCUIT_BREAKER_THRESHOLD`, `RECOVERY_TIMEOUT`)
- [ ] WebSocket message rate limits tested

### 4. Monitoring

- [ ] Structured logging enabled (`structlog`)
- [ ] Log aggregation configured (Datadog, Grafana Loki, CloudWatch, etc.)
- [ ] Health check endpoint verified: `curl http://localhost:8000/health`
- [ ] Metrics exported (Prometheus, StatsD, or custom)
- [ ] Alerts configured for critical errors

---

## Deployment options

### Option 1: Docker + PostgreSQL (Recommended)

**Use case:** Single-server deployment, easy scaling, full feature set.

#### Step 1: Prepare environment

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://genagent:STRONG_PASSWORD@db:5432/genagent

# LLM
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b

# Logging
LOG_LEVEL=INFO
ENABLE_STRUCTURED_LOGS=true

# Optional layers (disable for production unless needed)
ENABLE_BIASES=false
ENABLE_HRM=false
ENABLE_RLIF=false
ENABLE_GRAPHRAG=false
ENABLE_NEAT=false
```

#### Step 2: Deploy with Docker Compose

```bash
docker compose --profile postgres -f docker-compose.yml --env-file .env.production up -d
```

This starts:
- `app` (FastAPI server)
- `db` (PostgreSQL 16)
- `pgadmin` (optional, for DB management)

#### Step 3: Run migrations

```bash
docker compose exec app alembic upgrade head
```

#### Step 4: Verify health

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "tick": 0, ...}
```

#### Step 5: Monitor logs

```bash
docker compose logs -f app
```

---

### Option 2: Kubernetes (Scalable)

**Use case:** Multi-replica deployment, auto-scaling, high availability.

#### Prerequisites

- Kubernetes cluster (GKE, EKS, AKS, or self-hosted)
- `kubectl` configured
- PostgreSQL managed instance (Cloud SQL, RDS, etc.)

#### Step 1: Create secret for database URL

```bash
kubectl create secret generic gen-agent-secrets \
  --from-literal=DATABASE_URL="postgresql://user:pass@db-host:5432/genagent"
```

#### Step 2: Apply deployment manifest

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gen-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gen-agent
  template:
    metadata:
      labels:
        app: gen-agent
    spec:
      containers:
      - name: gen-agent
        image: your-registry/gen-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: gen-agent-secrets
              key: DATABASE_URL
        - name: LLM_PROVIDER
          value: "mock"  # or ollama/openrouter
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: gen-agent-service
spec:
  selector:
    app: gen-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Apply:

```bash
kubectl apply -f k8s/deployment.yaml
```

#### Step 3: Run migrations (one-time job)

Create `k8s/migration-job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: gen-agent-migrate
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: your-registry/gen-agent:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: gen-agent-secrets
              key: DATABASE_URL
      restartPolicy: Never
  backoffLimit: 3
```

Apply:

```bash
kubectl apply -f k8s/migration-job.yaml
kubectl logs job/gen-agent-migrate
```

#### Step 4: Verify deployment

```bash
kubectl get pods
kubectl logs -f deployment/gen-agent
kubectl port-forward service/gen-agent-service 8000:80
curl http://localhost:8000/health
```

---

### Option 3: Serverless (AWS Lambda / Google Cloud Run)

**Use case:** Event-driven, pay-per-use, automatic scaling.

**Note:** New Gen Agent is **stateful** (tick-based simulation), so serverless is only suitable for:
- Single-tick API endpoints (e.g., `/simulate-one-tick`)
- Batch processing (e.g., cron jobs to advance simulation)

For continuous simulations, use Docker or Kubernetes instead.

#### Example: Google Cloud Run

```bash
# Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/gen-agent

# Deploy
gcloud run deploy gen-agent \
  --image gcr.io/YOUR_PROJECT/gen-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars "DATABASE_URL=postgresql://...,LLM_PROVIDER=mock" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2
```

---

## Database setup

### PostgreSQL (recommended for production)

#### 1. Provision managed PostgreSQL

- **AWS RDS:** https://aws.amazon.com/rds/postgresql/
- **Google Cloud SQL:** https://cloud.google.com/sql/docs/postgres
- **Azure Database:** https://azure.microsoft.com/en-us/products/postgresql
- **DigitalOcean Managed DB:** https://www.digitalocean.com/products/managed-databases-postgresql

#### 2. Connection pooling

For high-concurrency workloads, use **PgBouncer**:

```yaml
# docker-compose.production.yml
services:
  pgbouncer:
    image: pgbouncer/pgbouncer
    environment:
      DATABASES_HOST: your-db-host.rds.amazonaws.com
      DATABASES_PORT: 5432
      DATABASES_USER: genagent
      DATABASES_PASSWORD: ${DB_PASSWORD}
      DATABASES_DBNAME: genagent
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
    ports:
      - "6432:6432"
```

Update `DATABASE_URL`:

```bash
DATABASE_URL=postgresql://genagent:pass@pgbouncer:6432/genagent
```

#### 3. Backup strategy

- **Automated backups:** Enable in cloud provider console (RDS, Cloud SQL)
- **Manual backup:**
  ```bash
  pg_dump -h your-db-host -U genagent genagent > backup.sql
  ```
- **Restore:**
  ```bash
  psql -h your-db-host -U genagent genagent < backup.sql
  ```

---

## LLM provider setup

### Ollama (self-hosted)

**Pros:** Free, private, full control  
**Cons:** Requires GPU, higher latency than cloud APIs

#### Deploy Ollama on separate server

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3.2:3b

# Run as service
ollama serve
```

#### Connect from app

```bash
OLLAMA_BASE_URL=http://ollama-server:11434
OLLAMA_MODEL=llama3.2:3b
```

### OpenRouter (cloud API)

**Pros:** 200+ models, pay-per-use, no infra  
**Cons:** Costs money, rate limits

```bash
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

**Free tier models:**
- `meta-llama/llama-3.2-3b-instruct:free`
- `google/gemini-flash-1.5:free`

**Pricing:** https://openrouter.ai/models

---

## Monitoring and observability

### 1. Structured logging

Enable JSON logs:

```bash
ENABLE_STRUCTURED_LOGS=true
LOG_LEVEL=INFO
```

Output format:

```json
{"event": "interaction", "agent_ids": ["a1", "a2"], "tick": 42, "timestamp": "2026-07-20T15:30:00Z"}
```

### 2. Log aggregation

Ship logs to centralized service:

#### Datadog

```yaml
# docker-compose.yml
services:
  app:
    logging:
      driver: "json-file"
      options:
        labels: "service=gen-agent,env=production"
  
  datadog-agent:
    image: datadog/agent:latest
    environment:
      DD_API_KEY: ${DD_API_KEY}
      DD_LOGS_ENABLED: true
      DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
```

#### Grafana Loki

```yaml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
  
  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    command: -config.file=/etc/promtail/config.yml
```

### 3. Metrics

Export simulation metrics to Prometheus:

Create `gen_agent/telemetry/prometheus.py`:

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

interactions_total = Counter("gen_agent_interactions_total", "Total interactions")
dialogues_total = Counter("gen_agent_dialogues_total", "Total dialogues")
tick_duration = Histogram("gen_agent_tick_duration_seconds", "Tick processing time")
active_agents = Gauge("gen_agent_active_agents", "Number of active agents")

# Start metrics server on port 9090
start_http_server(9090)
```

Scrape in `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'gen-agent'
    static_configs:
      - targets: ['app:9090']
```

### 4. Alerts

Example: Datadog monitor for high error rate

```json
{
  "name": "Gen Agent - High Error Rate",
  "type": "metric alert",
  "query": "avg(last_5m):sum:gen_agent.errors{env:production} > 10",
  "message": "Gen Agent error rate is high. Check logs for details. @slack-alerts",
  "priority": 2
}
```

---

## Security

### 1. API authentication

Add JWT authentication to FastAPI:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    if not is_valid_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return token
```

### 2. Rate limiting

Use `slowapi`:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/simulate")
@limiter.limit("10/minute")
async def simulate(request: Request):
    ...
```

### 3. HTTPS/TLS

Use reverse proxy (Nginx, Traefik) with Let's Encrypt:

```nginx
server {
    listen 443 ssl;
    server_name gen-agent.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Firewall

Allow only necessary ports:

```bash
ufw allow 22/tcp   # SSH
ufw allow 443/tcp  # HTTPS
ufw deny 8000/tcp  # Block direct access to FastAPI
ufw enable
```

---

## Scaling

### Horizontal scaling (multiple replicas)

1. **Stateless design:** Each replica should be stateless (use shared PostgreSQL for persistence)
2. **Load balancer:** Distribute traffic (Nginx, HAProxy, cloud LB)
3. **WebSocket sticky sessions:** Ensure clients reconnect to same replica

### Vertical scaling (larger instance)

- **CPU:** 4-8 cores for parallel agent processing
- **RAM:** 4-8 GB for large agent populations (100+)
- **Disk:** 50+ GB for long-running simulations with full memory retention

### Database scaling

- **Read replicas:** For read-heavy workloads (memory retrieval)
- **Partitioning:** Split `memories` table by `agent_id` or `created_at`
- **Archival:** Move old memories to cold storage (S3, Glacier)

---

## Troubleshooting

### High memory usage

**Cause:** Large agent populations, unbounded memory retention  
**Solution:** Enable memory compression (`ENABLE_MEMORY_COMPRESSION=true`), set retention policy

### Slow tick processing

**Cause:** LLM latency, blocking dialogues  
**Solution:** Use `block_on_dialogue=false`, tune `dialogue_wait_timeout_seconds`

### Database connection errors

**Cause:** Connection pool exhausted  
**Solution:** Increase `pool_size` in `SQLiteMemoryBackend` / PostgreSQL config

### LLM timeouts

**Cause:** Ollama overloaded, OpenRouter rate limit  
**Solution:** Enable circuit breaker, increase timeout, scale Ollama

---

## Next steps

- Set up CI/CD pipeline (GitHub Actions → Docker Hub → Kubernetes)
- Implement blue-green deployment for zero-downtime updates
- Add integration tests against production-like environment (staging)
- Set up disaster recovery plan (DB backups, rollback procedure)

## Resources

- [Docker best practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes production checklist](https://kubernetes.io/docs/setup/best-practices/)
- [PostgreSQL performance tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/)
