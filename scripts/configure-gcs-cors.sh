#!/bin/bash
# Configure GCS bucket CORS settings for image access from frontend

set -e

BUCKET_NAME="${GCS_BUCKET_NAME:-prompting-sandbox-mvp-multiprompt-uploads}"
FRONTEND_URL="${FRONTEND_URL:-https://multiprompt-frontend-*.a.run.app}"

echo "Configuring CORS for gs://${BUCKET_NAME}..."

# Create CORS configuration
cat > /tmp/cors-config.json <<EOF
[
  {
    "origin": ["${FRONTEND_URL}", "https://*.run.app", "http://localhost:4200"],
    "method": ["GET", "HEAD"],
    "responseHeader": ["Content-Type", "Content-Length", "Cache-Control"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Apply CORS configuration
gsutil cors set /tmp/cors-config.json gs://${BUCKET_NAME}

# Verify CORS configuration
echo "CORS configuration applied:"
gsutil cors get gs://${BUCKET_NAME}

# Cleanup
rm /tmp/cors-config.json

echo "✅ CORS configured successfully for gs://${BUCKET_NAME}"
