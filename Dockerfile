FROM python:3.11-slim

# Install comprehensive TeX Live packages (Overleaf-like capability)
# This provides support for: math, science, languages, graphics, bibliography, etc.
RUN apt-get update && apt-get install -y \
    # Core LaTeX engines
    texlive-luatex \
    texlive-xetex \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    # Math and science packages
    texlive-science \
    texlive-mathscience \
    # Fonts (comprehensive)
    texlive-fonts-recommended \
    texlive-fonts-extra \
    fonts-noto \
    fonts-noto-cjk \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-noto-ui-core \
    fonts-noto-ui-extra \
    fonts-noto-unhinted \
    fonts-liberation \
    fonts-dejavu \
    fonts-freefont-ttf \
    # Bengali fonts
    fonts-beng \
    fonts-beng-extra \
    # Language support (comprehensive)
    texlive-lang-other \
    texlive-lang-arabic \
    texlive-lang-chinese \
    texlive-lang-cyrillic \
    texlive-lang-european \
    texlive-lang-french \
    texlive-lang-german \
    texlive-lang-greek \
    texlive-lang-italian \
    texlive-lang-japanese \
    texlive-lang-korean \
    texlive-lang-spanish \
    # Bibliography and citations
    texlive-bibtex-extra \
    biber \
    # Graphics and diagrams
    texlive-pictures \
    texlive-pstricks \
    # Publishers and academic styles
    texlive-publishers \
    # Additional formats and utilities
    texlive-formats-extra \
    texlive-extra-utils \
    texlive-font-utils \
    # Games and special packages
    texlive-games \
    texlive-humanities \
    texlive-music \
    # LaTeX package manager
    texlive-plain-generic \
    # Additional utilities
    ghostscript \
    imagemagick \
    pdf2svg \
    poppler-utils \
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

