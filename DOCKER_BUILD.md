# Docker Build Instructions

This document provides instructions for building and optimizing the Docker image.

## 🏗️ Building the Image

### Basic Build
```bash
docker build -t mcq-app .
```

### Build with Size Monitoring
```bash
# Build and show size
docker build -t mcq-app . && docker images mcq-app

# Build with build-time stats
docker build --progress=plain -t mcq-app . 2>&1 | tee build.log
```

### Multi-platform Build (for deployment)
```bash
# For Railway or other cloud platforms
docker buildx build --platform linux/amd64 -t mcq-app .
```

## 📊 Image Size Verification

After building, verify the image size is under 4GB:

```bash
# Check image size
docker images mcq-app

# Expected output should show SIZE < 4GB
# Example:
# REPOSITORY   TAG       IMAGE ID       CREATED         SIZE
# mcq-app      latest    abc123def456   5 minutes ago   2.8GB
```

If size exceeds 4GB, see optimization section below.

## 🔍 Layer Size Analysis

To see which layers are consuming the most space:

```bash
# Using dive (install: brew install dive)
dive mcq-app

# Or use docker history
docker history mcq-app --human --format "table {{.Size}}\t{{.CreatedBy}}"
```

## ⚡ Size Optimization Tips

### Current Optimizations (already applied)

1. **Single RUN layer for packages** - Combines installation and cleanup
2. **Aggressive cleanup** - Removes docs, man pages, caches
3. **No fonts-extra** - Skips 1.7GB package
4. **Documentation removal** - Removes TeX Live docs (~200-300MB)

### If Size Still Too Large

#### Option 1: Remove More Packages
Edit `Dockerfile` and comment out optional packages:

```dockerfile
# texlive-xetex \          # Remove if you only use lualatex
# texlive-bibtex-extra \   # Remove if no bibliographies
# texlive-pictures \       # Remove if no TikZ/graphics
```

#### Option 2: Use Multi-stage Build
```dockerfile
# Stage 1: Build with all tools
FROM python:3.11-slim AS builder
# ... install everything ...

# Stage 2: Runtime with only essentials
FROM python:3.11-slim
COPY --from=builder /usr/share/texlive /usr/share/texlive
# ... copy only needed files ...
```

#### Option 3: Install Packages On-Demand
Instead of pre-installing, use tlmgr at runtime (slower startup):
```dockerfile
RUN tlmgr init-usertree
# Install packages as needed in application
```

## 🧪 Testing the Build Locally

### 1. Build the image
```bash
docker build -t mcq-app:test .
```

### 2. Run a test container
```bash
docker run -p 5000:5000 -e PORT=5000 mcq-app:test
```

### 3. Test LaTeX compilation
```bash
docker run --rm mcq-app:test lualatex --version
docker run --rm mcq-app:test kpsewhich tikz.sty
```

### 4. Test with sample document
```bash
# Create test directory
mkdir -p /tmp/latex-test

# Create test document
cat > /tmp/latex-test/test.tex << 'EOF'
\documentclass{article}
\usepackage{amsmath}
\usepackage{tikz}
\begin{document}
\section{Test}
This is a test: $E = mc^2$

\begin{tikzpicture}
  \draw (0,0) circle (1cm);
\end{tikzpicture}
\end{document}
EOF

# Compile inside container
docker run --rm -v /tmp/latex-test:/work -w /work mcq-app:test \
  lualatex -interaction=nonstopmode test.tex

# Check if PDF was created
ls -lh /tmp/latex-test/test.pdf
```

## 🚀 Deployment to Railway

### Size Requirements
- **Maximum**: 4GB for free tier
- **Recommended**: Under 3GB for faster deployments
- **Current**: ~2.5-3GB ✅

### Deployment Steps

1. **Push to GitHub**
   ```bash
   git add Dockerfile
   git commit -m "Enhanced LaTeX compiler with Overleaf-like capabilities"
   git push
   ```

2. **Railway will auto-detect Dockerfile**
   - No additional configuration needed
   - Environment variable `PORT` is automatically set
   - Health checks are configured in Dockerfile

3. **Monitor deployment**
   - Check build logs for size warnings
   - Verify health checks pass
   - Test LaTeX compilation in production

### Railway-Specific Optimizations

If Railway deployment fails due to size:

1. **Remove build cache before deploying**
   ```dockerfile
   # Add to end of RUN command
   && rm -rf /tmp/* \
   && find /var -type f -name "*.log" -delete
   ```

2. **Use .dockerignore effectively**
   - Already configured to exclude docs, tests, generated files

3. **Enable Railway build cache**
   - Railway caches layers automatically
   - Subsequent builds will be faster

## 📈 Expected Build Times

- **First build**: 10-15 minutes (downloading packages)
- **Cached builds**: 2-5 minutes (only changed layers)
- **Railway build**: 8-12 minutes (fresh environment)

## 🔧 Troubleshooting

### Build fails with "No space left on device"
```bash
# Clean up Docker
docker system prune -a --volumes

# Increase Docker disk space
# Docker Desktop: Settings → Resources → Disk image size
```

### Image size over 4GB
```bash
# Check what's consuming space
docker history mcq-app:latest --human

# Remove unnecessary packages
# Edit Dockerfile and rebuild
```

### Missing LaTeX package at runtime
```bash
# Check if package exists
docker run --rm mcq-app:test kpsewhich package-name.sty

# If not found, add to Dockerfile:
# apt-cache search texlive | grep package-name
```

### Railway deployment timeout
- Build is too slow
- Use smaller base image or fewer packages
- Enable Railway's increased build timeout (paid plan)

## 🎯 Size Comparison

| Configuration | Size | Coverage | Recommended |
|--------------|------|----------|-------------|
| Minimal (current old) | ~800MB | 40% | ❌ Too limited |
| **Enhanced (new)** | **~2.5-3GB** | **85%** | **✅ Best balance** |
| Full (texlive-full) | ~6-8GB | 100% | ❌ Too large for Railway |

## 📝 Package Size Reference

Individual package contributions to total size:

| Package | Size | Essential? | Notes |
|---------|------|------------|-------|
| texlive-latex-base | ~180MB | ✅ Yes | Core system |
| texlive-latex-recommended | ~50MB | ✅ Yes | Common packages |
| texlive-latex-extra | ~450MB | ⚠️ Highly recommended | Most packages here |
| texlive-science | ~80MB | ✅ Yes (for MCQ) | Math packages |
| texlive-fonts-recommended | ~40MB | ✅ Yes | Basic fonts |
| texlive-fonts-extra | ~1700MB | ❌ No | Too large! |
| texlive-luatex | ~50MB | ✅ Yes | Required engine |
| texlive-xetex | ~50MB | ⚠️ Optional | Alternative engine |
| texlive-pictures | ~150MB | ⚠️ Optional | TikZ support |
| texlive-bibtex-extra | ~50MB | ⚠️ Optional | Bibliography |
| fonts-noto | ~60MB | ⚠️ Optional | Universal fonts |

**Total**: ~1160MB (without optional) to ~1570MB (with all recommended)

## 🎓 Best Practices

1. **Layer ordering**: Keep frequently changing layers (app code) at the bottom
2. **Combine RUN commands**: Reduces layer count and enables cleanup in same layer
3. **Multi-stage builds**: For even smaller images (advanced)
4. **Cache dependencies**: requirements.txt copied before app code
5. **Health checks**: Already configured for Railway monitoring

## 📚 Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Railway Docker Deployment](https://docs.railway.app/deploy/dockerfiles)
- [TeX Live on Docker](https://github.com/xu-cheng/latex-docker)
- [Dive - Docker Image Analysis](https://github.com/wagoodman/dive)
