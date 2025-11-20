# Render Deployment Troubleshooting Guide

This guide helps fix the "Connection failed - please check if the API server is running and accessible" error on Render.

## 🔍 Quick Diagnosis

### Check These First:

1. **Is Render deploying?**
   - Go to Render Dashboard → Your Service
   - Check "Events" tab for status

2. **What's the error?**
   - Check "Logs" tab
   - Look for errors during build or runtime

3. **What's the build status?**
   - Building: Wait for it to finish
   - Failed: See solutions below
   - Success but not responding: Port binding issue

---

## ❌ Common Issues & Solutions

### Issue 1: PORT Binding Error
**Symptom**: "Can't find a port to bind" in logs

**Cause**: Hardcoded PORT in render.yaml conflicting with Render's dynamic PORT

**✅ Solution**: Already fixed in commit `b4f0284`
- render.yaml now lets Render inject PORT automatically
- Force a redeploy to apply the fix

**Steps**:
```bash
# Force redeploy with latest code
git pull origin main  # Or your branch
# Then in Render Dashboard:
# Manual Deploy → Clear build cache & deploy
```

---

### Issue 2: Docker Image Too Large
**Symptom**: Build timeout, "out of memory", or extremely slow deployment

**Cause**: Enhanced Dockerfile with LaTeX packages (~2.5-3GB image)

**Current Size**: ~2.5-3GB (under 4GB Railway limit, but might be tight for Render free tier)

**✅ Solution A**: Wait longer - First build takes 15-20 minutes

**✅ Solution B**: Use minimal Dockerfile (if build fails)

```bash
# Temporarily use minimal Dockerfile
# In Render Dashboard:
# Settings → Docker Command → Dockerfile Path
# Change from: ./Dockerfile
# Change to: ./Dockerfile.minimal
# Then: Manual Deploy

# This reduces image to ~800MB but with fewer LaTeX packages
```

**✅ Solution C**: Remove optional LaTeX packages

Edit `Dockerfile` and comment out these lines:
```dockerfile
# texlive-xetex \         # Save ~50MB
# texlive-bibtex-extra \  # Save ~50MB
# texlive-pictures \      # Save ~150MB
# fonts-noto \            # Save ~60MB
```

This saves ~310MB, bringing image to ~2.2GB

---

### Issue 3: Health Check Failing
**Symptom**: "Health check timeout" or "Service unhealthy"

**Cause**: App not responding on correct port or taking too long to start

**✅ Solution**:

1. **Check start.sh binds correctly**:
```bash
# start.sh already correct:
PORT=${PORT:-5000}
gunicorn web.app:app --bind "0.0.0.0:${PORT}"
```

2. **Increase health check wait time** in Dockerfile:
```dockerfile
# Already set to 40s start period:
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s
```

3. **If LaTeX image is slow to start**, increase in render.yaml:
```yaml
healthCheckPath: /health
startCommand: /app/start.sh  # Make sure this is set
```

---

### Issue 4: Authentication/Session Issues
**Symptom**: API endpoints return 401/403 errors

**Cause**: New auth toggle changes affecting session handling

**✅ Solution**: Check auth settings

**If auth is DISABLED**:
- Users access as 'guest'
- No login required
- Should work for public access

**If auth is ENABLED** (default):
- Users must log in first
- Session cookie must be sent with API requests (automatic)
- Render must have session secret set

Check in `web/app.py`:
```python
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
```

**Fix for production**:
1. Go to Render Dashboard → Your Service
2. Environment → Add Environment Variable
3. Add: `SECRET_KEY` = (generate random string)
```bash
# Generate random secret key:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### Issue 5: Build Cache Issues
**Symptom**: Old code still running despite new commits

**Cause**: Render caching old Docker layers

**✅ Solution**: Clear cache and redeploy

**Steps**:
1. Render Dashboard → Your Service
2. **Manual Deploy** button → **Clear build cache & deploy**
3. Wait for fresh build (10-15 minutes for full image)

---

## 🚀 Recommended Fix Steps

### Step 1: Force Fresh Deployment

```bash
# Ensure latest code is pushed
git status
git log --oneline -3

# Should see these recent commits:
# b4f0284 Fix: Remove hardcoded PORT from render.yaml
# 019754e Add admin toggle to disable authentication globally
# 1c266f5 Enhance LaTeX compiler with Overleaf-like capabilities
```

### Step 2: In Render Dashboard

1. Go to your service
2. Click **"Manual Deploy"**
3. Select **"Clear build cache & deploy"**
4. **Wait 10-20 minutes** for initial build (LaTeX packages are large)

### Step 3: Monitor Deployment

Watch the logs for:
```
✅ Successfully built Docker image
✅ Listening at: http://0.0.0.0:10000
✅ Health check passed
✅ Deployed successfully
```

### Step 4: Test the Deployment

Once deployed, test:
```bash
# Replace with your Render URL
curl https://your-app.onrender.com/health

# Should return:
# {"status":"healthy","service":"mcq-app"}
```

---

## 📊 Deployment Size Reference

| Configuration | Size | Build Time | Render Free Tier |
|---------------|------|------------|------------------|
| Minimal (Dockerfile.minimal) | ~800MB | 3-5 min | ✅ Fast |
| **Enhanced (Dockerfile)** | **~2.5-3GB** | **10-20 min** | **✅ Should work** |
| Full TeX Live (not used) | ~6-8GB | 30+ min | ❌ Too large |

**Current configuration**: Enhanced (good balance of features vs size)

---

## 🐛 Still Not Working?

### Check Render Logs for Specific Errors:

1. **Build Stage Errors**:
```bash
# Look for:
ERROR: failed to solve: ...
unable to install package ...
```

2. **Runtime Errors**:
```bash
# Look for:
ModuleNotFoundError: ...
ImportError: ...
Address already in use: ...
```

3. **Port Binding Errors**:
```bash
# Look for:
Can't find a port to bind
Failed to bind to 0.0.0.0:...
```

### Get Help:

1. Copy error logs from Render
2. Check if PORT is set: `echo $PORT` in Render shell
3. Check if app starts locally:
```bash
docker build -t mcq-test .
docker run -p 10000:10000 -e PORT=10000 mcq-test
curl http://localhost:10000/health
```

---

## ✅ Expected Working Configuration

After fixing, you should see in Render logs:

```
=== Build Stage ===
[+] Building Docker image...
Successfully built image (2.8GB)

=== Deploy Stage ===
Starting gunicorn...
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: sync
[INFO] Booting worker with pid: 1

=== Health Check ===
Health check passed ✓

=== Status ===
🟢 Live
```

---

## 📚 Related Documentation

- [Render Docker Deployment](https://render.com/docs/docker)
- [DOCKER_BUILD.md](./DOCKER_BUILD.md) - Image size optimization
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Full deployment guide
- [LATEX_PACKAGES.md](./LATEX_PACKAGES.md) - Package details

---

## 🎯 Summary

**Most Likely Fix**: Force redeploy with build cache cleared

```bash
# In Render Dashboard:
1. Manual Deploy → Clear build cache & deploy
2. Wait 15-20 minutes for build
3. Check logs for successful deployment
4. Test: https://your-app.onrender.com/health
```

**If Build Fails**: Use Dockerfile.minimal temporarily

**If Still Failing**: Check logs and report specific error message
