FROM python:3.11-slim

# Install TeX Live with math and Bengali support
RUN apt-get update && apt-get install -y \
    texlive-luatex \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-science \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-lang-other \
    fonts-beng \
    fonts-beng-extra \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

# Rebuild LuaLaTeX font cache to recognize installed fonts
RUN luaotfload-tool --update || true

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

