# Deployment Guide

This guide covers deploying the MCQ Application to various free hosting platforms and running it locally with one command.

## Table of Contents

1. [Quick Start (One-Click Run)](#quick-start-one-click-run)
2. [Deploy to Railway](#deploy-to-railway)
3. [Deploy to Render](#deploy-to-render)
4. [Deploy to Fly.io](#deploy-to-flyio)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start (One-Click Run)

### Option 1: Using the Script (Recommended)

```bash
# Make the script executable (first time only)
chmod +x run.sh

# Run the application
./run.sh
```

The script will:
- ✅ Check if Docker is installed
- ✅ Create necessary directories
- ✅ Build and start the application
- ✅ Display access URLs

### Option 2: Using Makefile

```bash
# Install Make (if not already installed)
# Ubuntu/Debian: sudo apt-get install make
# macOS: Already installed

# Run the application
make run

# View other commands
make help
```

### Option 3: Using Docker Compose Directly

```bash
docker compose up --build -d
```

### Available Makefile Commands

```bash
make help      # Show all available commands
make run       # Start the application
make stop      # Stop the application
make restart   # Restart the application
make logs      # View logs
make status    # Check status
make health    # Check health endpoint
make clean     # Clean up containers and volumes
```

---

## Deploy to Railway

[Railway](https://railway.app) offers a free tier with generous limits. Perfect for Docker applications.

### Prerequisites

- GitHub account
- Railway account (sign up at https://railway.app)

### Steps

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy via Railway Dashboard**:
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will automatically detect `railway.json` and deploy

3. **Configure Environment Variables** (if needed):
   - Go to your project settings
   - Add environment variables if required
   - Railway automatically sets `PORT` environment variable

4. **Access Your Application**:
   - Railway will provide a public URL (e.g., `https://your-app.railway.app`)
   - The application will be accessible at this URL

### Using Railway CLI (Optional)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Railway Configuration

The `railway.json` file configures:
- Health check endpoint (`/health`)
- Restart policies
- Build settings

---

## Deploy to Render

[Render](https://render.com) offers a free tier with automatic deployments from GitHub.

### Prerequisites

- GitHub account
- Render account (sign up at https://render.com)

### Steps

1. **Push your code to GitHub** (if not already done)

2. **Create a Web Service on Render**:
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Configure Settings**:
   - **Name**: `mcq-app` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `/` (root of repository)
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Context**: `.`
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`

4. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - First deployment takes 5-10 minutes

5. **Access Your Application**:
   - Render provides a URL: `https://mcq-app.onrender.com`
   - Free tier: App sleeps after 15 minutes of inactivity (takes ~30s to wake)

### Render Configuration

The `render.yaml` file configures:
- Docker build settings
- Health check endpoint
- Environment variables
- Auto-deploy settings

---

## Deploy to Fly.io

[Fly.io](https://fly.io) offers a free tier with great performance and global distribution.

### Prerequisites

- GitHub account
- Fly.io account (sign up at https://fly.io)
- Fly CLI installed

### Steps

1. **Install Fly CLI**:
   ```bash
   # macOS/Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login to Fly.io**:
   ```bash
   flyctl auth login
   ```

3. **Initialize Fly.io App** (first time only):
   ```bash
   # This creates fly.toml from the existing one
   flyctl launch
   # Answer prompts or use existing fly.toml
   ```

4. **Deploy**:
   ```bash
   flyctl deploy
   ```

5. **Access Your Application**:
   - Fly.io provides a URL: `https://mcq-app.fly.dev`
   - Your app is globally distributed

### Fly.io Configuration

The `fly.toml` file configures:
- App name and region
- HTTP service settings
- Health checks
- VM resources (512MB RAM on free tier)

### Scale (Optional)

```bash
# Scale to multiple instances (paid feature)
flyctl scale count 2
```

---

## Best Practices

### 1. Environment Variables

Always use environment variables for configuration:

```python
# In web/app.py
PORT = int(os.environ.get("PORT", 5000))
HOST = os.environ.get("HOST", "0.0.0.0")
```

### 2. Health Checks

All deployment platforms support health checks via `/health` endpoint:

```python
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"}), 200
```

### 3. Logging

Use proper logging for production:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 4. Resource Limits

Configure appropriate resource limits:
- **Railway**: 512MB RAM (free tier)
- **Render**: 512MB RAM (free tier)
- **Fly.io**: 512MB RAM (free tier)

### 5. Data Persistence

⚠️ **Important**: Free tiers typically use **ephemeral storage**. Your data will be lost when:
- The container restarts (Render)
- You redeploy (all platforms)
- The container is stopped (Fly.io free tier)

**Solutions**:
- Use external storage (S3, database) for production
- For development/testing, data persists as long as the container runs
- Consider upgrading to a paid plan for persistent storage

### 6. Security

- ✅ Never commit secrets to Git
- ✅ Use environment variables for sensitive data
- ✅ Enable HTTPS (automatic on all platforms)
- ✅ Use proper CORS settings if needed

### 7. Monitoring

Monitor your application:
- **Railway**: Built-in metrics dashboard
- **Render**: Built-in logs and metrics
- **Fly.io**: `flyctl logs` or built-in dashboard

---

## Troubleshooting

### Application Won't Start

1. **Check logs**:
   ```bash
   # Local
   docker compose logs
   
   # Railway
   railway logs
   
   # Render
   Check dashboard logs
   
   # Fly.io
   flyctl logs
   ```

2. **Verify health check**:
   ```bash
   curl http://localhost:5000/health
   ```

3. **Check port binding**:
   - Make sure `PORT` environment variable is set
   - Application binds to `0.0.0.0:${PORT}`

### LaTeX Compilation Errors

1. **Check TeX Live installation**:
   ```bash
   # Inside container
   docker compose exec mcq-app bash
   lualatex --version
   ```

2. **Rebuild font cache**:
   ```bash
   luaotfload-tool --update
   ```

### PDF Generation Fails

1. **Check permissions**:
   ```bash
   ls -la web/generated/
   ```

2. **Check disk space**:
   - Free tiers have limited storage
   - Clean up old generated PDFs periodically

### Build Timeouts

- **Solution**: Optimize Dockerfile
  - Multi-stage builds
  - Cache layers properly
  - Use `.dockerignore`

### Out of Memory

- **Solution**: Increase resource limits or optimize
  - Reduce gunicorn workers (from 2 to 1)
  - Optimize LaTeX compilation
  - Upgrade to paid tier if needed

---

## Comparison of Free Hosting Options

| Feature | Railway | Render | Fly.io |
|---------|---------|--------|--------|
| **Free Tier** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Auto Deploy** | ✅ Yes | ✅ Yes | ✅ Yes |
| **HTTPS** | ✅ Automatic | ✅ Automatic | ✅ Automatic |
| **Sleep Mode** | ❌ No | ✅ Yes (15min) | ⚠️ Auto-stop |
| **Persistent Storage** | ⚠️ Ephemeral | ⚠️ Ephemeral | ⚠️ Ephemeral |
| **Global CDN** | ❌ No | ❌ No | ✅ Yes |
| **CLI Tool** | ✅ Yes | ❌ No | ✅ Yes |
| **Build Time** | ~5 min | ~5-10 min | ~5 min |

---

## Recommendations

- **For Development/Testing**: Use local Docker (`./run.sh` or `make run`)
- **For Quick Deploy**: Use **Railway** (simplest setup)
- **For GitHub Integration**: Use **Render** (excellent GitHub integration)
- **For Global Distribution**: Use **Fly.io** (best performance worldwide)

---

## Next Steps

1. Choose a hosting platform
2. Deploy using the steps above
3. Monitor your application
4. Set up automatic backups (for production data)
5. Consider upgrading to paid tier for production use

---

## Support

For issues or questions:
- Check logs: `docker compose logs` or platform-specific logs
- Review this guide's troubleshooting section
- Check platform-specific documentation

