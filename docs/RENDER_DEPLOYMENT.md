# Deploy to Render.com - Complete Guide

This guide will help you deploy your Fraud Detection Platform to Render.com for free and make it accessible from anywhere.

## Prerequisites

- GitHub account with the repository pushed (✅ Already done)
- Render.com account (free)

## Step-by-Step Deployment

### 1. Visit Render.com

1. Go to https://render.com
2. Click **Sign Up** (or **Sign In** if you already have an account)
3. Use your GitHub account to sign up/login (recommended)

### 2. Create a New Web Service

1. Click **Dashboard** in the top right
2. Click **New +** button
3. Select **Web Service**
4. Click **Connect** next to your GitHub account if not already connected

### 3. Select Repository

1. Search for **fintech-risk-agent**
2. Click **Connect** next to your repository
3. Authorize Render to access your GitHub account

### 4. Configure Deployment

Fill in the deployment settings:

| Field | Value |
|-------|-------|
| **Name** | `fraud-detection-api` |
| **Environment** | `Python 3` |
| **Region** | Select closest to you (e.g., `Virginia (us-east)`) |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn src.api.transaction_handler:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` |

### 5. Environment Variables (Optional)

No environment variables needed for this project, but you can add:

```
PYTHONUNBUFFERED=true
```

### 6. Deploy

1. Click **Create Web Service**
2. Render will automatically deploy your service
3. Wait for the deployment to complete (2-5 minutes)

You'll see the deployment logs in real-time. Once complete, you'll get a URL like:

```
https://your-service-name.onrender.com
```

## After Deployment

### ✅ Test Your Live Application

1. Visit your service URL in browser
2. You should see the beautiful fraud detection dashboard
3. Try uploading the sample CSV file

### 📤 Share Your URL

Your application is now publicly accessible. Share the URL with anyone to let them:
- Upload transaction files
- Analyze for fraud patterns
- View risk profiles
- Download reports

### 📝 Usage Examples

**Upload a file:**
```
1. Navigate to https://your-service-name.onrender.com
2. Drag and drop your CSV file or click to select
3. Wait for analysis (takes 5-10 seconds)
4. View results with charts and risk profiles
```

**Download sample test file:**
```
The sample_transactions.csv file is in your GitHub repo
Download it and test your live deployment
```

## API Endpoints (Optional)

Your deployment also has all API endpoints available:

```
GET  https://your-service-name.onrender.com/health
GET  https://your-service-name.onrender.com/metrics
POST https://your-service-name.onrender.com/score
POST https://your-service-name.onrender.com/upload-and-analyze
POST https://your-service-name.onrender.com/analyze-transactions
GET  https://your-service-name.onrender.com/api-docs
```

## Troubleshooting

### Service Won't Start
1. Check the deploy logs in Render dashboard
2. Ensure all dependencies are in requirements.txt
3. Check for Python version compatibility

### Upload Fails
1. Ensure file is under 10MB (Render free tier limit)
2. Check CSV format (needs transaction_id, amount, user_id, etc.)
3. Check browser console for error messages

### Slow Performance
Render free tier has limitations:
- Service sleeps after 15 minutes of inactivity
- May take 30 seconds to wake up on first request
- Limited compute resources

**Solution:** Upgrade to Render's paid tier for continuous deployment

## Production Improvements

For production deployment, consider:

1. **Upgrade Plan**: Switch from Free to Starter ($7/month)
   - No automatic sleep
   - Better performance
   - 100GB bandwidth

2. **Add Redis Cache** (optional)
   ```
   Cache analysis results to speed up repeated queries
   ```

3. **Database** (optional)
   ```
   Store analysis history and user data
   PostgreSQL on Render: $15/month
   ```

4. **Environment Variables**
   ```
   Add secrets for API keys if needed
   ```

## Monitoring

In Render Dashboard:
- View real-time logs
- Check metrics (CPU, memory, bandwidth)
- Monitor deployments
- Set up alerts (paid feature)

## URL Pattern

Your service URL will be:
```
https://fraud-detection-api.onrender.com
OR
https://[your-custom-name].onrender.com
```

You can customize the name in Service Settings → Instance → Name

## Get Help

- **Render Docs**: https://render.com/docs
- **Service Logs**: Check the Logs tab in your Render dashboard
- **GitHub Issues**: Post in your repo if something breaks

---

## Quick Reference: Your Dashboard URLs

After deployment:

| URL | Purpose |
|-----|---------|
| `https://your-url/` | Main fraud detection dashboard |
| `https://your-url/dashboard` | Same as above |
| `https://your-url/api-docs` | API documentation (Swagger) |
| `https://your-url/api-redoc` | API documentation (ReDoc) |

Enjoy your live fraud detection platform! 🚀
