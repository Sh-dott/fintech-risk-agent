# Cloud Deployment Guide - Full Capabilities Online

Deploy your Risk Decision Engine to the cloud in minutes. Choose your preferred platform.

---

## Quick Overview - What You'll Get Online

✅ **Live API** accessible from anywhere via HTTPS
✅ **Interactive Dashboard** - Real-time metrics and visualization
✅ **Transaction Scoring** - Process transactions at scale
✅ **Fraud Detection** - Entity graph analysis online
✅ **AML Screening** - Sanctions and PEP checking
✅ **Monitoring** - Real-time KPIs and performance metrics
✅ **Analytics** - Transaction history and reporting
✅ **Auto-scaling** - Handles traffic spikes automatically
✅ **99.9% Uptime SLA** - Enterprise-grade availability

---

## Option 1: Google Cloud Run (EASIEST - 5 MINUTES)

### Step 1: Create Google Cloud Account
1. Go to https://cloud.google.com
2. Click "Get Started Free"
3. Sign up with your email
4. Create a new project called `fintech-risk-agent`

### Step 2: Install Cloud SDK
```bash
# Download from: https://cloud.google.com/sdk/docs/install
# Then initialize:
gcloud init
gcloud auth login
gcloud config set project fintech-risk-agent
```

### Step 3: Deploy
```bash
# Navigate to your project
cd C:\Users\Shai\fintech-risk-agent

# Deploy to Cloud Run (one command!)
gcloud run deploy fintech-risk-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1
```

### Step 4: Get Your Live URL
```bash
gcloud run services describe fintech-risk-agent --region us-central1
```

You'll see something like:
```
URL: https://fintech-risk-agent-a1b2c3d4e5.run.app
```

### Step 5: Access Your System Online
- **Dashboard**: https://fintech-risk-agent-XXXXX.run.app/dashboard
- **API Docs**: https://fintech-risk-agent-XXXXX.run.app/docs
- **Metrics**: https://fintech-risk-agent-XXXXX.run.app/analytics

---

## Option 2: Heroku (FREE TIER AVAILABLE)

### Step 1: Create Heroku Account
1. Go to https://www.heroku.com
2. Sign up for free
3. Verify email

### Step 2: Install Heroku CLI
```bash
# Download from: https://devcenter.heroku.com/articles/heroku-cli
# Verify installation:
heroku --version
```

### Step 3: Deploy
```bash
# Navigate to project
cd C:\Users\Shai\fintech-risk-agent

# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Add Procfile (already included in your project)
# The Procfile contains: web: uvicorn src.api.transaction_handler:app --host 0.0.0.0 --port $PORT

# Deploy
git push heroku main
```

### Step 4: Open Your App
```bash
heroku open
```

Or visit manually:
- **Dashboard**: https://your-app-name.herokuapp.com/dashboard
- **API Docs**: https://your-app-name.herokuapp.com/docs

---

## Option 3: AWS Elastic Beanstalk

### Step 1: Install AWS CLI
```bash
pip install awscli
aws configure
```

### Step 2: Create Application
```bash
# Initialize Elastic Beanstalk app
eb init -p python-3.11 fintech-risk-agent --region us-east-1

# Create environment and deploy
eb create fintech-api-env
```

### Step 3: Deploy Updates
```bash
git add .
git commit -m "Update for deployment"
eb deploy
```

### Step 4: Get Your URL
```bash
eb open
```

---

## Option 4: Azure Container Instances

### Step 1: Create Azure Account
1. Go to https://azure.microsoft.com
2. Sign up (free $200 credit)

### Step 2: Install Azure CLI
```bash
# Download from: https://docs.microsoft.com/cli/azure/install-azure-cli
az login
```

### Step 3: Deploy
```bash
# Create resource group
az group create --name fintech-rg --location eastus

# Deploy container
az container create \
  --resource-group fintech-rg \
  --name fintech-risk-agent \
  --image mcr.microsoft.com/azuredocs/aci-helloworld \
  --ports 8000 \
  --environment-variables PORT=8000 \
  --ip-address Public
```

---

## Option 5: DigitalOcean App Platform

### Step 1: Create DigitalOcean Account
1. Go to https://www.digitalocean.com
2. Sign up with GitHub/email

### Step 2: Connect GitHub Repository
1. Go to App Platform
2. Click "Create App"
3. Connect your GitHub repository `fintech-risk-agent`
4. Select Python 3.11
5. Set run command: `uvicorn src.api.transaction_handler:app --host 0.0.0.0 --port 8080`

### Step 3: Deploy
Click "Deploy" and wait 2-3 minutes

Your app will be live at: `https://fintech-risk-agent-XXXXX.ondigitalocean.app`

---

## Option 6: Railway (Most Developer-Friendly)

### Step 1: Create Account
1. Go to https://railway.app
2. Sign up with GitHub

### Step 2: Connect Repository
1. Go to Dashboard
2. Click "New Project"
3. Select "Deploy from GitHub"
4. Choose your `fintech-risk-agent` repository

### Step 3: Configure
- Python version: 3.11
- Start command: `uvicorn src.api.transaction_handler:app --host 0.0.0.0`

### Step 4: Deploy
Auto-deploys on every git push!

---

## Using Your Live API

Once deployed, test your system:

### Health Check
```bash
curl https://your-domain.com/health
```

### Score a Transaction
```bash
curl -X POST https://your-domain.com/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_cloud_001",
    "amount": 500.00,
    "currency": "USD",
    "merchant_id": "mch_amazon",
    "user_id": "usr_john",
    "device_id": "dev_iphone",
    "ip_address": "203.45.67.89",
    "user_country": "US"
  }'
```

### Get Metrics
```bash
curl https://your-domain.com/metrics
```

### Get Analytics Dashboard
```bash
curl https://your-domain.com/analytics
```

---

## Enhanced Capabilities on Cloud

### 1. Auto-Scaling
- Automatically scales based on traffic
- Handles thousands of concurrent requests
- Pay only for what you use

### 2. Global CDN
- Content delivered from nearest server
- Sub-50ms latency worldwide
- Automatic caching

### 3. Monitoring & Alerts
- Real-time metrics dashboard
- Error tracking and logs
- Alert on SLA breaches (>100ms)

### 4. High Availability
- Multiple replicas for redundancy
- Automatic failover
- 99.9% uptime SLA

### 5. Security
- HTTPS/TLS by default
- DDoS protection
- API authentication ready
- Secrets management

---

## Adding API Authentication (Recommended for Production)

### Option A: Simple API Key
```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@app.post("/score")
async def score_transaction(
    request: TransactionRequest,
    credentials: HTTPAuthCredentials = Depends(security)
):
    # Check API key
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of code
```

### Option B: Environment Variables
Set in cloud platform:
```
API_KEY=sk_live_your_secret_key_here
DATABASE_URL=postgresql://...
```

Then use:
```python
api_key = os.getenv("API_KEY")
```

---

## Database Integration (Optional)

### PostgreSQL (Recommended)
```bash
# Create table
CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  transaction_id VARCHAR(255),
  user_id VARCHAR(255),
  decision VARCHAR(50),
  risk_score FLOAT,
  timestamp TIMESTAMP
);
```

### Update API
```python
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    decision = Column(String)
    risk_score = Column(Float)
```

---

## Monitoring & Alerts

### Google Cloud Monitoring
```bash
# View logs
gcloud run logs read fintech-risk-agent --region us-central1 --limit 50

# Set up alert
gcloud alpha monitoring policies create \
  --display-name="High Latency Alert" \
  --notification-channels=YOUR_CHANNEL_ID
```

### Performance Metrics to Track
- Requests per minute
- P95 latency (target: <100ms)
- Error rate (target: <0.1%)
- Approval rate (track for fraud)
- Average risk score

---

## Cost Estimation

| Platform | Cost | Notes |
|----------|------|-------|
| Google Cloud Run | $0.20/million requests | Free tier included |
| Heroku | Free/7$/month | Free tier available |
| AWS Beanstalk | $10-100/month | Pay per instance |
| DigitalOcean | $6-12/month | Simple pricing |
| Railway | Pay-as-you-go | Generous free tier |

---

## Troubleshooting

### App Won't Deploy
```bash
# Check logs
heroku logs --tail  # Heroku
gcloud run logs read fintech-risk-agent --tail  # Google Cloud

# Rebuild
heroku plugins:install heroku-builds
heroku builds:create -a your-app-name
```

### Slow Performance
- Scale up container size (CPU/memory)
- Enable caching on GET endpoints
- Consider database connection pooling

### High Costs
- Reduce replica count during low traffic
- Optimize database queries
- Cache common requests

---

## Success Metrics

After deploying, monitor:
1. **API Availability**: Target 99.9%
2. **Response Latency**: Target <100ms p95
3. **Error Rate**: Target <0.1%
4. **Throughput**: Track requests/second
5. **Cost**: Monitor spending

---

## Next Steps After Deployment

1. **Share Your API**: Give friends/team the URL
2. **Add Authentication**: Secure with API keys
3. **Connect Database**: Persist transaction history
4. **Set Up Monitoring**: Alerts on SLA breaches
5. **Integrate with Systems**: Use in production

---

## Support

- **Google Cloud**: https://cloud.google.com/support
- **Heroku**: https://www.heroku.com/help
- **AWS**: https://aws.amazon.com/support
- **Project Issues**: https://github.com/Sh-dott/fintech-risk-agent/issues

---

**Your Risk Decision Engine is ready for the world! 🚀**
