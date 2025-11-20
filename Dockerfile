FROM python:3.11-slim

# Install enhanced TeX Live packages for powerful LaTeX compilation
# Optimized to stay under 4GB (similar to Overleaf capabilities)
# Strategy: Add most commonly used packages while avoiding bloat
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core LaTeX
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    # Math & Science packages
    texlive-science \
    # Fonts (recommended only, extra is 1.7GB!)
    texlive-fonts-recommended \
    fonts-liberation \
    # Bengali fonts (required)
    fonts-beng \
    fonts-noto \
    # LuaTeX engine (essential for lualatex)
    texlive-luatex \
    # XeTeX engine (modern font support)
    texlive-xetex \
    # Graphics & TikZ packages
    texlive-pictures \
    # Bibliography support
    texlive-bibtex-extra \
    # Essential utilities
    ghostscript \
    poppler-utils \
    # Aggressive cleanup in same layer to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/doc/* \
    && rm -rf /usr/share/man/* \
    && rm -rf /usr/share/info/* \
    && rm -rf /usr/share/locale/* \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/log/* \
    # Remove TeX Live documentation (saves ~200-300MB)
    && rm -rf /usr/share/texlive/texmf-dist/doc/* \
    && rm -rf /usr/share/texmf/doc/* \
    # Remove TeX Live source files
    && rm -rf /usr/share/texlive/texmf-dist/source/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding start.sh to avoid overwriting)
COPY . .

# Copy and set execute permissions for startup script
COPY --chmod=755 start.sh /app/start.sh
RUN ls -la /app/start.sh

# Create necessary directories that might not exist in repo
RUN mkdir -p web/generated web/answers web/sessions web/answer_keys

# Expose port (default 5000, can be overridden by PORT env var)
EXPOSE 5000

# Add health check (checks if the app responds to /health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; import os; port=os.environ.get('PORT', '5000'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# Use gunicorn to run the Flask app
# Note: app.py is in the web directory, so we need to adjust the module path
# Use startup script which properly handles PORT environment variable
CMD ["/app/start.sh"]

