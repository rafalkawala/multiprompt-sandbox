#!/bin/bash
set -e

# Configuration
PROJECT_ID="prompting-sandbox-mvp"
REGION="us-central1"
DB_INSTANCE="multiprompt-db"
DB_NAME="multiprompt"
DB_USER="multiprompt"

echo "=== MultiPrompt Sandbox GCP Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Enable required APIs
echo "Step 1: Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# Step 2: Create Artifact Registry repository
echo "Step 2: Creating Artifact Registry..."
gcloud artifacts repositories create multiprompt \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID \
  --description="MultiPrompt Sandbox container images" \
  2>/dev/null || echo "Repository already exists"

# Step 3: Create Cloud SQL instance
echo "Step 3: Creating Cloud SQL instance..."
if ! gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID &>/dev/null; then
  gcloud sql instances create $DB_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --project=$PROJECT_ID \
    --root-password=$(openssl rand -base64 32)

  # Create database
  gcloud sql databases create $DB_NAME \
    --instance=$DB_INSTANCE \
    --project=$PROJECT_ID

  # Create user
  DB_PASSWORD=$(openssl rand -base64 32)
  gcloud sql users create $DB_USER \
    --instance=$DB_INSTANCE \
    --password=$DB_PASSWORD \
    --project=$PROJECT_ID

  echo "Database user password: $DB_PASSWORD"
  echo "SAVE THIS PASSWORD - you'll need it for environment variables"
else
  echo "Cloud SQL instance already exists"
fi

# Step 4: Create secrets
echo "Step 4: Setting up secrets..."
echo ""
echo "Please create the following secrets in Secret Manager:"
echo ""
echo "  # Database password (generated above during DB creation)"
echo "  echo 'YOUR_DB_PASSWORD' | gcloud secrets create multiprompt-db-password --data-file=- --project=$PROJECT_ID"
echo ""
echo "  # Application secret key (generate a random one)"
echo "  openssl rand -base64 32 | gcloud secrets create multiprompt-secret-key --data-file=- --project=$PROJECT_ID"
echo ""
echo "  # Google OAuth credentials (from Google Cloud Console)"
echo "  echo 'YOUR_CLIENT_ID' | gcloud secrets create google-client-id --data-file=- --project=$PROJECT_ID"
echo "  echo 'YOUR_CLIENT_SECRET' | gcloud secrets create google-client-secret --data-file=- --project=$PROJECT_ID"
echo ""
echo "  # Gemini API key (from Google AI Studio)"
echo "  echo 'YOUR_API_KEY' | gcloud secrets create multiprompt-gemini-api-key --data-file=- --project=$PROJECT_ID"
echo ""

# Step 5: Build and deploy
echo "Step 5: Starting Cloud Build..."
gcloud builds submit \
  --config=cloudbuild.yaml \
  --project=$PROJECT_ID \
  --substitutions=COMMIT_SHA=$(git rev-parse HEAD)

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Get service URLs:"
echo "  gcloud run services describe multiprompt-backend --region=$REGION --format='value(status.url)'"
echo "  gcloud run services describe multiprompt-frontend --region=$REGION --format='value(status.url)'"
