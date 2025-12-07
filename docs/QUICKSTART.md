# Quick Start Guide

Get the Risk Decision Engine API running in 5 minutes.

---

## 🚀 Start Locally (Fastest)

### 1. Clone & Install

```bash
git clone https://github.com/Sh-dott/fintech-risk-agent.git
cd fintech-risk-agent
pip install -r requirements.txt
```

### 2. Run the API

```bash
python -m uvicorn src.api.transaction_handler:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 3. Open in Browser

Visit: **http://localhost:8000/docs**

You'll see the interactive API documentation (Swagger UI) with all endpoints and test buttons.

---

## 📝 Test the API

### Using Browser (Easiest)

1. Go to http://localhost:8000/docs
2. Click "Try it out" on the `/score` endpoint
3. Fill in the example:
   ```json
   {
     "transaction_id": "txn_123",
     "amount": 100.00,
     "currency": "USD",
     "merchant_id": "mch_456",
     "user_id": "usr_789",
     "device_id": "dev_abc",
     "ip_address": "192.168.1.1",
     "user_country": "US"
   }
   ```
4. Click "Execute"
5. See the decision result

### Using cURL

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

### Using Python

```python
import requests

response = requests.post("http://localhost:8000/score", json={
    "transaction_id": "txn_123",
    "amount": 100.00,
    "currency": "USD",
    "merchant_id": "mch_456",
    "user_id": "usr_789",
    "device_id": "dev_abc",
    "ip_address": "192.168.1.1",
    "user_country": "US"
})

print(response.json())
```

### Using JavaScript/Node.js

```javascript
fetch('http://localhost:8000/score', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    transaction_id: 'txn_123',
    amount: 100.00,
    currency: 'USD',
    merchant_id: 'mch_456',
    user_id: 'usr_789',
    device_id: 'dev_abc',
    ip_address: '192.168.1.1',
    user_country: 'US'
  })
})
.then(r => r.json())
.then(data => console.log(data))
```

---

## 📊 Example Response

```json
{
  "decision": "allow",
  "risk_score": 0.135,
  "risk_level": "low",
  "reason_codes": ["LOW_RISK"],
  "next_actions": ["APPROVE", "MONITOR"],
  "compliance_log_id": "clog_fb6b916a",
  "latency_ms": 12.5,
  "explanation": "Decision based on 1 key signals: Normal Behavior Pattern (0.07); Normal Velocity (0.05); Amount Under Limit (0.05)",
  "timestamp": "2025-10-28T18:05:00.123456"
}
```

---

## 🐳 Run with Docker

### Build

```bash
docker build -t fintech-risk-agent .
```

### Run

```bash
docker run -p 8000:8000 fintech-risk-agent
```

Then visit: http://localhost:8000/docs

---

## ☁️ Deploy to Cloud (1 Command)

### Google Cloud Run (Easiest)

```bash
gcloud run deploy fintech-risk-agent --source . --allow-unauthenticated
```

### Heroku

```bash
heroku create your-app-name
git push heroku main
heroku open
```

### AWS

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions

---

## 🔧 Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API status |
| `/score` | POST | Score a single transaction |
| `/batch-score` | POST | Score multiple transactions |
| `/docs` | GET | Interactive API documentation |
| `/redoc` | GET | Alternative API documentation |

---

## 📚 API Documentation

### Interactive (Recommended)
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Static
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed API docs

---

## ❌ Troubleshooting

### Port 8000 Already in Use

```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
python -m uvicorn src.api.transaction_handler:app --port 8001
```

### Module Not Found Error

```bash
# Make sure you're in the project directory
cd fintech-risk-agent

# Install dependencies
pip install -r requirements.txt
```

### Can't Connect to API

```bash
# Check if API is running
curl http://localhost:8000/health

# If not running, make sure to run:
python -m uvicorn src.api.transaction_handler:app --reload
```

---

## 📖 Learn More

- **Full Deployment Guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **README**: [README.md](./README.md)
- **GitHub Issues**: https://github.com/Sh-dott/fintech-risk-agent/issues

---

## 🎯 What's Next?

1. ✅ Run locally and explore the API
2. Deploy to cloud (Heroku, Google Cloud, AWS)
3. Add authentication & rate limiting
4. Store transaction history in database
5. Set up monitoring & alerts
6. Integrate with your payment system

---

**Happy scoring!** 🚀
