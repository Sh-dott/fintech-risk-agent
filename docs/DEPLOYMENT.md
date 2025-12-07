# Deployment Guide

Deploy the Risk Decision Engine API online for real-time transaction scoring.

---

## 🚀 Option 1: Local Development (Fastest)

### Prerequisites
- Python 3.11+
- Git

### Run Locally

```bash
# Clone repository
git clone https://github.com/Sh-dott/fintech-risk-agent.git
cd fintech-risk-agent

# Install dependencies
pip install -r requirements.txt

# Run API server
python -m uvicorn src.api.transaction_handler:app --reload --host 0.0.0.0 --port 8000
```

**Access API:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

---

## 🐳 Option 2: Docker (Recommended for Production)

### Prerequisites
- Docker installed

### Build & Run

```bash
# Build Docker image
docker build -t fintech-risk-agent .

# Run container
docker run -p 8000:8000 fintech-risk-agent
```

**Access API:**
- http://localhost:8000/docs

---

## ☁️ Option 3: Deploy to Heroku (Free/Paid)

### Prerequisites
- Heroku account (https://www.heroku.com)
- Heroku CLI installed

### Deploy

```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create your-app-name

# Add Procfile (already included) - specifies how to run the app
# Deploy
git push heroku main

# View logs
heroku logs --tail
```

**Access API:**
```
https://your-app-name.herokuapp.com/docs
```

---

## ☁️ Option 4: AWS (Elastic Container Service)

### Prerequisites
- AWS account
- AWS CLI configured

### Deploy with ECS

```bash
# Create ECR repository
aws ecr create-repository --repository-name fintech-risk-agent

# Build and push Docker image
docker build -t fintech-risk-agent .
docker tag fintech-risk-agent:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/fintech-risk-agent:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/fintech-risk-agent:latest

# Create ECS task definition, service, cluster (via AWS Console or CDK)
```

**Access API:**
```
http://your-load-balancer-url/docs
```

---

## ☁️ Option 5: Google Cloud Run (Easiest)

### Prerequisites
- Google Cloud account
- Cloud SDK installed

### Deploy

```bash
# Authenticate
gcloud auth login

# Build and deploy
gcloud run deploy fintech-risk-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Get service URL
gcloud run services describe fintech-risk-agent --region us-central1
```

**Access API:**
```
https://fintech-risk-agent-XXXXX.run.app/docs
```

---

## ☁️ Option 6: Azure Container Instances

### Prerequisites
- Azure account
- Azure CLI installed

### Deploy

```bash
# Authenticate
az login

# Build Docker image
docker build -t fintech-risk-agent .

# Create container registry
az acr create --resource-group myResourceGroup --name myregistry --sku Basic

# Push image
docker tag fintech-risk-agent myregistry.azurecr.io/fintech-risk-agent:latest
docker push myregistry.azurecr.io/fintech-risk-agent:latest

# Deploy to ACI
az container create --resource-group myResourceGroup --name fintech-risk-agent \
  --image myregistry.azurecr.io/fintech-risk-agent:latest \
  --ports 8000 --ip-address Public
```

---

## 📊 API Usage Examples

### Health Check

```bash
curl http://localhost:8000/health
```

### Score a Transaction

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_123",
    "amount": 100.00,
    "currency": "USD",
    "merchant_id": "mch_456",
    "user_id": "usr_789",
    "device_id": "dev_abc",
    "ip_address": "192.168.1.1",
    "user_country": "US"
  }'
```

**Response:**
```json
{
  "decision": "allow",
  "risk_score": 0.135,
  "risk_level": "low",
  "reason_codes": ["LOW_RISK"],
  "next_actions": ["APPROVE", "MONITOR"],
  "compliance_log_id": "clog_xyz",
  "latency_ms": 12.5,
  "explanation": "Decision based on normal behavior patterns...",
  "timestamp": "2025-10-28T18:05:00.123456"
}
```

### Batch Score Transactions

```bash
curl -X POST http://localhost:8000/batch-score \
  -H "Content-Type: application/json" \
  -d '[
    {
      "transaction_id": "txn_1",
      "amount": 50.00,
      "currency": "USD",
      "merchant_id": "mch_1",
      "user_id": "usr_1",
      "device_id": "dev_1",
      "ip_address": "192.168.1.1",
      "user_country": "US"
    },
    {
      "transaction_id": "txn_2",
      "amount": 200.00,
      "currency": "USD",
      "merchant_id": "mch_2",
      "user_id": "usr_2",
      "device_id": "dev_2",
      "ip_address": "192.168.1.2",
      "user_country": "UK"
    }
  ]'
```

---

## 🔐 Security Considerations

### Production Checklist

- [ ] Enable HTTPS/TLS (use load balancer or reverse proxy)
- [ ] Add API authentication (API keys, OAuth2)
- [ ] Rate limiting (prevent abuse)
- [ ] Request validation (input sanitization)
- [ ] Logging & monitoring (CloudWatch, Datadog, etc.)
- [ ] Database for transaction history (PostgreSQL, MongoDB)
- [ ] Secrets management (environment variables, AWS Secrets Manager)
- [ ] CORS configuration (restrict to trusted domains)
- [ ] WAF (Web Application Firewall)

### Example: Add Authentication

```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@app.post("/score")
async def score_transaction(
    request: TransactionRequest,
    credentials: HTTPAuthCredentials = Depends(security)
):
    # Validate API key from credentials.credentials
    if credentials.credentials != "your-secret-api-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of logic
```

---

## 📈 Scaling & Performance

### Optimization Tips

1. **Caching**: Cache common decision patterns
2. **Load Balancing**: Distribute requests across multiple instances
3. **Database**: Store transaction history for analytics
4. **Async Processing**: Use background tasks for heavy work
5. **CDN**: Cache static content
6. **Auto-scaling**: Configure horizontal pod autoscaling (Kubernetes)

### Example: Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fintech-risk-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fintech-risk-agent
  template:
    metadata:
      labels:
        app: fintech-risk-agent
    spec:
      containers:
      - name: api
        image: fintech-risk-agent:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: fintech-risk-agent
spec:
  selector:
    app: fintech-risk-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## 📊 Monitoring & Logging

### Add Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, make_asgi_app

request_count = Counter('risk_engine_requests_total', 'Total requests')
decision_histogram = Histogram('risk_engine_latency_seconds', 'Decision latency')

@app.post("/score")
async def score_transaction(request: TransactionRequest):
    request_count.inc()
    with decision_histogram.time():
        # ... decision logic
```

### View Metrics
```
http://localhost:8000/metrics
```

---

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
python -m uvicorn src.api.transaction_handler:app --port 8001
```

### Module Not Found
```bash
# Ensure you're in project root
cd fintech-risk-agent
pip install -r requirements.txt
```

### Docker Build Fails
```bash
# Clear Docker cache and rebuild
docker build --no-cache -t fintech-risk-agent .
```

---

## 📞 Support

- **GitHub Issues**: https://github.com/Sh-dott/fintech-risk-agent/issues
- **Documentation**: http://localhost:8000/docs

---

**Happy deploying!** 🚀
