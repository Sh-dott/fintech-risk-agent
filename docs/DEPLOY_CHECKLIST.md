# Render Deployment Checklist

Use this checklist to deploy your fraud detection platform to Render.

## ✅ Pre-Deployment Checklist

- [x] All code committed to GitHub
- [x] requirements.txt updated with all dependencies
- [x] Procfile configured correctly
- [x] render.yaml created
- [x] Dashboard tested locally
- [x] File upload working
- [x] API endpoints functional
- [x] No syntax errors
- [x] All dependencies installed

## 📋 Deployment Steps

### Step 1: Access Render Dashboard
- [ ] Go to https://dashboard.render.com
- [ ] Log in with GitHub account
- [ ] You should see your "fraud-detection-api" service

### Step 2: Select Your Service
- [ ] Click on "fraud-detection-api" service
- [ ] Verify service name is correct
- [ ] Check that it's connected to your GitHub repo

### Step 3: Redeploy Service
**Option A: Using Web Dashboard (Recommended)**
- [ ] Click the service name
- [ ] Navigate to **Deployments** tab
- [ ] Click **Deploy** button (latest commit)
- [ ] Wait for status to change to "Live" (green dot)
- [ ] Takes 2-5 minutes

**Option B: Auto-Deploy from GitHub**
- [ ] Just commit and push changes to main branch
- [ ] Render auto-detects and deploys
- [ ] Check Deployments tab for progress

### Step 4: Verify Deployment
- [ ] Status shows "Live" (green dot)
- [ ] No error logs in "Logs" tab
- [ ] Visit your service URL
- [ ] Dashboard loads without errors
- [ ] File upload works

### Step 5: Test the Platform
- [ ] Open main URL (e.g., https://fraud-detection-api.onrender.com)
- [ ] See beautiful dashboard
- [ ] Try uploading sample_transactions.csv
- [ ] View analysis results
- [ ] Click "Clear Results" button
- [ ] Click "Download Report" button

### Step 6: Share with Users
- [ ] Copy your Render URL
- [ ] Share URL with team/users
- [ ] Create documentation for users
- [ ] Test from different devices

## 🔧 Troubleshooting During Deployment

### Bad Gateway Error
**Status**: ✅ FIXED (lazy-load engine)

See: `RENDER_FIX.md`

### Build Failed
- [ ] Check build logs in Render dashboard
- [ ] Look for dependency errors
- [ ] Verify Python version (3.11)
- [ ] Check requirements.txt syntax

### Service Won't Start
- [ ] Click "Logs" tab
- [ ] Look for startup errors
- [ ] Check if all dependencies installed
- [ ] Verify Procfile is correct

### Dashboard Not Loading
- [ ] Check browser console (F12)
- [ ] Verify URL is correct
- [ ] Try clearing cache
- [ ] Try different browser
- [ ] Check Render logs

### File Upload Fails
- [ ] Ensure file is < 10MB
- [ ] Check file format (CSV/JSON/Excel)
- [ ] Verify column names in CSV
- [ ] Check browser console errors

## 📊 Performance Notes

**First Request Latency**
- Dashboard load: <500ms ✓
- First /score request: ~5-10s (engine initializes)
- Subsequent requests: <500ms ✓

**Render Free Tier Limits**
- Cold start: May wake up after 15 min inactivity (30s)
- Bandwidth: 100GB/month
- Compute: Shared resources
- Storage: No persistent storage (data doesn't persist)

## 🎯 Success Criteria

You'll know deployment worked when:

✅ Service status is "Live" (green dot)
✅ Dashboard loads at your Render URL
✅ Can upload CSV files
✅ Analysis completes in <15 seconds
✅ Results display with charts
✅ Clear button resets dashboard
✅ Download button exports JSON
✅ No errors in browser console

## 📝 URLs After Deployment

Once live, you'll have:

| URL | Purpose |
|-----|---------|
| `https://your-service.onrender.com/` | Main dashboard |
| `https://your-service.onrender.com/dashboard` | Same as above |
| `https://your-service.onrender.com/api-docs` | API documentation |
| `https://your-service.onrender.com/classic` | Old dashboard |

## 🚨 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Bad Gateway | See RENDER_FIX.md |
| Build failed | Check requirements.txt versions |
| Dashboard white screen | Clear browser cache, F12 console |
| Upload button missing | Wait for JS to load, refresh page |
| File won't upload | Check file size < 10MB, format correct |
| Analysis hangs | Cold start may take 30s, wait more |
| 404 errors | Verify URL, check service is "Live" |

## 📞 Getting Help

1. **Check Logs**: Render dashboard → Logs tab
2. **Read RENDER_FIX.md**: Troubleshooting guide
3. **Check Documentation**: DASHBOARD_FEATURES.md, RENDER_DEPLOYMENT.md
4. **GitHub Issues**: Report bugs in your repo

## ✨ After Successful Deployment

### Share Your Platform
```
Hey! Check out my fraud detection platform:
https://your-service-name.onrender.com

Upload transaction data to analyze for fraud patterns!
```

### Monitor Your Service
- Check Render dashboard weekly
- Monitor logs for errors
- Track bandwidth usage
- Monitor CPU/memory

### Future Improvements
- Upgrade to Starter plan ($7/month) for better performance
- Add database for history
- Implement user authentication
- Create mobile app

## 📚 Documentation Files

Read these in order:
1. **RENDER_FIX.md** - Fix Bad Gateway
2. **DASHBOARD_FEATURES.md** - UI features
3. **RENDER_DEPLOYMENT.md** - Full guide
4. **This file** - Deployment checklist

## ✅ Final Status

- [x] Code ready
- [x] Dependencies fixed
- [x] Deployment configured
- [x] Tested locally
- [x] Documentation complete

**READY TO DEPLOY! 🚀**

---

**Next Step**: Follow the deployment steps above, then visit your live URL!
