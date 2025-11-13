# Docker Setup Guide for Ubuntu

This guide will help you run the MCQ application on a fresh Ubuntu machine using Docker.

## Prerequisites

You need Docker and Docker Compose installed on your Ubuntu machine.

## Important Note: Windows vs Ubuntu Differences

**Font Configuration:**
- **Windows:** The template originally used "Nirmala UI" font
- **Ubuntu/Linux:** The template has been updated to use "Noto Sans Bengali" which is available on Linux
- The Dockerfile installs all necessary Bengali fonts and rebuilds the font cache automatically

**LaTeX Compiler:**
- Both systems use LuaLaTeX, but the Docker container uses TeX Live for Linux
- All necessary packages (polyglossia, amsmath, etc.) are installed in the container

## Step 1: Install Docker and Docker Compose

### Install Docker

```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (to run docker without sudo)
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect
# Or run: newgrp docker
```

**Note:** After adding yourself to the docker group, you need to log out and log back in (or restart your terminal session) for the changes to take effect.

### Verify Docker Installation

```bash
docker --version
docker compose version
```

## Step 2: Transfer Your Project to Ubuntu

You have several options:

### Option A: Using Git (Recommended if using version control)

```bash
# Install git if not already installed
sudo apt-get install -y git

# Clone your repository (replace with your repo URL)
git clone <your-repository-url> mcq
cd mcq
```

### Option B: Using SCP (from your Windows machine)

From your Windows PowerShell or Command Prompt:

```powershell
# Replace with your Ubuntu server details
scp -r C:\Users\HP\Documents\MCQxm\mcq username@ubuntu-server-ip:/home/username/
```

Then on Ubuntu:

```bash
cd ~/mcq
```

### Option C: Using USB Drive or other method

Copy the project folder to your Ubuntu machine, then:

```bash
cd /path/to/mcq/project
```

## Step 3: Build and Run the Docker Container

### Using Docker Compose (Recommended)

```bash
# Make sure you're in the project root directory
cd /path/to/mcq

# Build and start the container
docker compose up --build -d

# View logs (optional)
docker compose logs -f

# Stop the container
docker compose down

# Restart the container
docker compose restart
```

The `-d` flag runs the container in detached mode (in the background).

### Using Docker directly

```bash
# Build the image
docker build -t mcq-app .

# Run the container
docker run -d \
  --name mcq-app \
  -p 5000:5000 \
  -v $(pwd)/web/generated:/app/web/generated \
  -v $(pwd)/web/answers:/app/web/answers \
  -v $(pwd)/web/sessions:/app/web/sessions \
  -v $(pwd)/web/answer_keys:/app/web/answer_keys \
  mcq-app

# View logs
docker logs -f mcq-app

# Stop the container
docker stop mcq-app

# Remove the container
docker rm mcq-app
```

## Step 4: Access the Application

Once the container is running, you can access the application:

- **Local access:** Open `http://localhost:5000` in your browser
- **Network access:** Open `http://<ubuntu-machine-ip>:5000` from other devices on the same network

To find your Ubuntu machine's IP address:

```bash
# Find IP address
ip addr show | grep "inet " | grep -v 127.0.0.1
# or
hostname -I
```

## Step 5: Firewall Configuration (if needed)

If you can't access the application from other devices, you may need to open port 5000 in the firewall:

```bash
# Check if ufw is active
sudo ufw status

# Allow port 5000
sudo ufw allow 5000/tcp

# If ufw is not installed, install it
sudo apt-get install -y ufw
sudo ufw enable
sudo ufw allow 5000/tcp
```

## Useful Commands

### View running containers

```bash
docker ps
# or
docker compose ps
```

### View container logs

```bash
docker compose logs -f mcq-app
```

### Execute commands inside the container

```bash
docker compose exec mcq-app bash
```

### Rebuild after code changes

```bash
docker compose up --build -d
```

### Stop and remove everything

```bash
docker compose down
```

### Clean up Docker (remove unused images, containers, etc.)

```bash
docker system prune -a
```

## Troubleshooting

### Permission denied errors

If you get permission errors when running Docker commands:

```bash
# Make sure you're in the docker group
groups

# If docker is not in the list, add yourself and log out/in
sudo usermod -aG docker $USER
newgrp docker
```

### Port already in use

If port 5000 is already in use:

```bash
# Check what's using port 5000
sudo lsof -i :5000
# or
sudo netstat -tlnp | grep 5000

# Stop the process or change the port in docker-compose.yml
```

### Container won't start

```bash
# Check logs for errors
docker compose logs mcq-app

# Try running without -d to see output
docker compose up
```

### PDF compilation errors

The container includes TeX Live with Bengali support. If you still get font errors:

```bash
# Enter the container
docker compose exec mcq-app bash

# Rebuild font cache
luaotfload-tool -u

# Exit container
exit
```

## Production Deployment Notes

For production use, consider:

1. **Use a reverse proxy** (nginx) in front of the application
2. **Set up HTTPS** using Let's Encrypt
3. **Configure proper logging**
4. **Set up regular backups** of the data volumes
5. **Monitor container health** and set up auto-restart policies

Example nginx configuration (if needed):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Auto-start on Boot

To automatically start the container when the system boots:

```bash
# Create a systemd service (optional)
sudo nano /etc/systemd/system/mcq-app.service
```

Add this content:

```ini
[Unit]
Description=MCQ Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/mcq
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcq-app.service
sudo systemctl start mcq-app.service
```

Replace `/path/to/mcq` with your actual project path.

