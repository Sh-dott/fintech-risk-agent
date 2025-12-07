# RENDER DEPLOYMENT FIX - Bad Gateway Issue

Got a "Bad Gateway" error on Render? Follow these steps to fix it.

## What Happened

The "Bad Gateway" error occurs when Render can't start your service within the timeout window. This was because the `RiskDecisionEngine` was initializing on startup, which took too long.

## What We Fixed

✅ **Lazy Loading**: The engine now loads only when first needed, not at startup
✅ **Fast Startup**: Dashboard serves immediately
✅ **Graceful Fallback**: If engine fails, API still works with degraded features

## How to Redeploy

### Option 1: Using Render Dashboard (Recommended)

1. **Go to Render**: https://dashboard.render.com
2. **Find your service**: Look for "fraud-detection-api"
3. **Redeploy**:
   - Click the service
   - Click **Deployments** tab
   - Click **Deploy** button (the latest commits are fetched automatically)
4. **Wait**: Takes 2-5 minutes
5. **Check Status**: Should say "Live" with a green dot

### Option 2: Using Git (Auto-Deploy)

Since Render watches your GitHub repository, just push the latest code:

```bash
cd C:\Users\Shai\fintech-risk-agent
git pull origin main
# Then Render will automatically redeploy
```

The fix is already committed and pushed, so just wait for Render to detect it.

## After Redeployment

### Test Your Service

1. **Visit your Render URL**:
   ```
   https://your-service-name.onrender.com
   ```

2. **You should see**:
   - Beautiful fraud detection dashboard ✓
   - Upload button working ✓
   - File upload capability ✓

3. **If it works**:
   - Share the URL with users
   - Upload CSV files to test
   - Download reports

## If Still Getting Bad Gateway

### Check the Logs

1. **In Render Dashboard**:
   - Click your service
   - Click **Logs** tab
   - Look for error messages

### Common Issues

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | `requirements.txt` might be missing dependencies |
| `Address already in use` | Port conflict (shouldn't happen on Render) |
| `TimeoutError` | Application still taking too long to start |
| No startup logs | Service is crashing before startup |

### If Dependencies Missing

1. **Check `requirements.txt`** has all dependencies:
   ```
   pip install -r requirements.txt
   ```

2. **Update locally, test, then commit**:
   ```bash
   pip install [missing-package]
   pip freeze > requirements.txt
   git add requirements.txt
   git commit -m "Add missing dependencies"
   git push origin main
   ```

3. **Redeploy** on Render

## Features That Now Work

✅ **Dashboard** - Loads instantly
✅ **File Upload** - Full functionality
✅ **Analysis** - Advanced fraud detection
✅ **Risk Profiles** - Entity analysis
✅ **Visualizations** - Charts and tables
✅ **Download Reports** - JSON export
✅ **Clear Results** - Reset dashboard

## URL Structure

After successful deployment:

| Page | URL |
|------|-----|
| Main Dashboard | `https://your-url` |
| Dashboard (alt) | `https://your-url/dashboard` |
| API Docs | `https://your-url/api-docs` |
| API ReDoc | `https://your-url/api-redoc` |

## Performance Notes

**First Request Latency**:
- First request to `/score` or `/batch-score` will be slower (~5-10s) because engine initializes
- Subsequent requests are fast (<500ms)
- Dashboard loads instantly regardless

**Why This Design**:
- Render free tier has limited startup time
- Lazy loading prevents timeout
- Users get dashboard immediately
- Engine loads only when needed

## Share Your Platform

Once live, share the URL with anyone:

```
Hey! Check out my fraud detection platform:
https://your-service-name.onrender.com

Upload transaction data to analyze for fraud patterns!
```

## Need Help?

1. **Check Render Logs**: Always check the logs tab first
2. **Review RENDER_DEPLOYMENT.md**: Full deployment guide
3. **Check GitHub Issues**: Report bugs in the repo

## Success! 🎉

You now have a live fraud detection platform accessible from anywhere!

The fix has been tested locally and is production-ready. Happy analyzing!
