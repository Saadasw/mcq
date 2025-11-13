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

# Copy application code
COPY . .

# Create necessary directories that might not exist in repo
RUN mkdir -p web/generated web/answers web/sessions web/answer_keys

# Expose port 5000
EXPOSE 5000

# Use gunicorn to run the Flask app
# Note: app.py is in the web directory, so we need to adjust the module path
CMD ["gunicorn", "web.app:app", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "2"]

