# Quick Start Guide

Get the MCQ Application running in seconds with one command!

## Prerequisites

- Docker installed ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (comes with Docker Desktop, or install separately)

## One-Command Setup

### Option 1: Using the Script (Easiest)

```bash
chmod +x run.sh
./run.sh
```

That's it! The script will:
- ✅ Check Docker installation
- ✅ Create necessary directories
- ✅ Build the Docker image
- ✅ Start the application
- ✅ Show you the access URL

### Option 2: Using Make

```bash
make run
```

### Option 3: Docker Compose Directly

```bash
docker compose up --build -d
```

## Access Your Application

Once running, open your browser:

- **Local**: http://localhost:5000
- **Network**: http://YOUR-IP:5000

## Useful Commands

```bash
# View logs
docker compose logs -f

# Stop application
docker compose down

# Restart application
docker compose restart

# Check status
docker compose ps

# View health check
curl http://localhost:5000/health
```

## What's Next?

- 📖 Read [DEPLOYMENT.md](./DEPLOYMENT.md) to deploy to free hosting
- 🔧 Read [DOCKER_SETUP.md](./DOCKER_SETUP.md) for detailed setup instructions
- 📚 Check the main [README.md](./README.md) for project overview

## Troubleshooting

**Permission denied?**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Port already in use?**
```bash
# Change port in docker-compose.yml
ports:
  - "8000:5000"  # Use port 8000 instead
```

**Want to deploy to the cloud?**
See [DEPLOYMENT.md](./DEPLOYMENT.md) for Railway, Render, and Fly.io guides.

