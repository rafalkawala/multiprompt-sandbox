# Deployment Guide

## Prerequisites

Before deploying, ensure you have:

- [ ] Google Cloud Platform account with billing enabled
- [ ] `gcloud` CLI installed and configured
- [ ] `terraform` installed (v1.0+)
- [ ] Docker installed
- [ ] Gemini API key
- [ ] GitHub repository set up

## Infrastructure Overview

The platform uses a serverless architecture on Google Cloud:

- **Cloud Run** - Serverless container platform for frontend and backend
- **Cloud SQL** - Managed PostgreSQL database
- **Cloud Storage** - Image and file storage
- **Secret Manager** - Secure credential storage
- **Artifact Registry** - Docker image storage

## Initial GCP Setup

### 1. Set Up GCP Project

```bash
# Set project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage-component.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Create Artifact Registry

```bash
# Create repository for Docker images
gcloud artifacts repositories create multiprompt-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for MLLM Benchmarking Platform"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3. Create Secrets

```bash
# Create secret for Gemini API key
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-

# Verify secret
gcloud secrets list
```

## Terraform Deployment

### 1. Configure Terraform Variables

```bash
cd terraform

# Create terraform.tfvars with your values
cat > terraform.tfvars << EOF
gcp_project_id      = "your-project-id"
gcp_project_name    = "MLLM Benchmarking Platform"
gcp_billing_account = "your-billing-account-id"
gcp_region          = "us-central1"
gcp_zone            = "us-central1-c"
EOF
```

### 2. Initialize and Apply Terraform

```bash
# Initialize Terraform
terraform init

# Preview infrastructure changes
terraform plan

# Apply infrastructure (creates Cloud SQL, VPC, etc.)
terraform apply

# Save outputs for later use
terraform output > ../terraform-outputs.txt
```

### 3. Build and Deploy Services

```bash
# Build Docker images
docker build -t gcr.io/$PROJECT_ID/multiprompt-frontend:v1 ./frontend
docker build -t gcr.io/$PROJECT_ID/multiprompt-backend:v1 ./backend

# Push to GCR
docker push gcr.io/$PROJECT_ID/multiprompt-frontend:v1
docker push gcr.io/$PROJECT_ID/multiprompt-backend:v1

# Deploy backend to Cloud Run
gcloud run deploy mllm-backend-svc \
    --image gcr.io/$PROJECT_ID/multiprompt-backend:v1 \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID" \
    --set-secrets "GEMINI_API_KEY=gemini-api-key:latest"

# Deploy frontend to Cloud Run
gcloud run deploy mllm-frontend-svc \
    --image gcr.io/$PROJECT_ID/multiprompt-frontend:v1 \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

## Local Development

### Using Docker Compose

```bash
# Create .env file in backend directory
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Without Docker

**Frontend:**
```bash
cd frontend
npm install
ng serve
# Access at http://localhost:4200
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload
# Access at http://localhost:8000
```

## GitHub Actions Setup

### 1. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions"

# Get service account email
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter="displayName:GitHub Actions" \
    --format='value(email)')

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# Create and download key
gcloud iam service-accounts keys create key.json \
    --iam-account=$SA_EMAIL
```

### 2. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and add:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | Contents of key.json file |
| `GEMINI_API_KEY` | Your Gemini API key |

## Continuous Deployment

Once GitHub Actions is configured:

1. Push code to `main` branch
2. GitHub Actions will automatically:
   - Run tests
   - Build Docker images
   - Push to Container Registry
   - Deploy to Cloud Run

## Monitoring

### View Logs

```bash
# View backend logs
gcloud run services logs read mllm-backend-svc --region us-central1

# Stream logs
gcloud run services logs tail mllm-backend-svc --region us-central1
```

### Check Service Status

```bash
# List all Cloud Run services
gcloud run services list --region us-central1

# Describe specific service
gcloud run services describe mllm-backend-svc --region us-central1

# Get service URL
gcloud run services describe mllm-backend-svc --region us-central1 --format 'value(status.url)'
```

## Rollback

```bash
# List revisions
gcloud run revisions list --service mllm-backend-svc --region us-central1

# Traffic to specific revision
gcloud run services update-traffic mllm-backend-svc \
    --to-revisions REVISION_NAME=100 \
    --region us-central1
```

## Troubleshooting

### Service not starting

```bash
# Check service logs
gcloud run services logs read mllm-backend-svc --region us-central1 --limit 100

# Check service details
gcloud run services describe mllm-backend-svc --region us-central1
```

### Image pull errors

```bash
# Verify image exists
gcloud container images list --repository gcr.io/$PROJECT_ID

# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID
```

### Database connection issues

```bash
# Check Cloud SQL instance
gcloud sql instances describe mllm-sandbox-db-instance

# Test connection from Cloud Run
# Ensure VPC connector is configured properly
```

## Cleanup

```bash
# Delete Cloud Run services
gcloud run services delete mllm-frontend-svc --region us-central1
gcloud run services delete mllm-backend-svc --region us-central1

# Destroy Terraform infrastructure
cd terraform
terraform destroy

# Delete Artifact Registry
gcloud artifacts repositories delete multiprompt-repo --location=us-central1
```

## Cost Optimization

1. **Cloud Run auto-scaling** - Scales to zero when not in use
2. **Set minimum instances to 0** - No cost when idle
3. **Use appropriate CPU/memory** - Start small, scale as needed
4. **Cloud SQL** - Use db-g1-small for development
5. **Clean up unused resources** - Delete old revisions and images

## Environment-Specific Configuration

### Development
- Use Docker Compose locally
- SQLite or local PostgreSQL
- Mock external services

### Staging/UAT
- Deploy to Cloud Run with reduced resources
- Use Cloud SQL (db-g1-small)
- Separate GCP project recommended

### Production
- Full Cloud Run deployment
- Cloud SQL with appropriate tier
- Enable Cloud Armor for security
- Configure custom domain
- Set up monitoring and alerting
