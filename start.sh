#!/bin/sh
# Startup script that handles PORT environment variable
# Railway and other platforms set PORT dynamically

PORT=${PORT:-5000}

exec gunicorn web.app:app \
    --bind "0.0.0.0:${PORT}" \
    --timeout 120 \
    --workers 2 \
    --access-logfile - \
    --error-logfile -

