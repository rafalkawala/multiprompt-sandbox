# Deployment Guide

## Prerequisites

Before deploying, ensure you have:

- [ ] Google Cloud Platform account with billing enabled
- [ ] `gcloud` CLI installed and configured
- [ ] `kubectl` installed
- [ ] Docker installed
- [ ] Gemini API key
- [ ] GitHub repository set up

## Initial GCP Setup

### 1. Set Up GCP Project

```bash
# Set project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 2. Create GKE Cluster

```bash
# Create cluster
gcloud container clusters create multiprompt-cluster \
    --num-nodes=3 \
    --machine-type=e2-medium \
    --zone=us-central1-a \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=5 \
    --enable-stackdriver-kubernetes

# Get credentials
gcloud container clusters get-credentials multiprompt-cluster \
    --zone=us-central1-a
```

### 3. Create Artifact Registry

```bash
# Create repository for Docker images
gcloud artifacts repositories create multiprompt-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for MultiPrompt Sandbox"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 4. Create Secrets

```bash
# Create Kubernetes secret for Gemini API key
kubectl create secret generic app-secrets \
    --from-literal=gemini-api-key=YOUR_GEMINI_API_KEY \
    -n multiprompt-sandbox

# Verify secret
kubectl get secrets -n multiprompt-sandbox
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
    --role="roles/container.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

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
| `GKE_CLUSTER_NAME` | multiprompt-cluster |
| `GKE_ZONE` | us-central1-a |

### 3. Update Kubernetes Manifests

```bash
# Update PROJECT_ID in deployment files
cd k8s/base
sed -i 's/PROJECT_ID/your-actual-project-id/g' *.yaml

# Update ConfigMap with your GCP project ID
kubectl apply -f configmap.yaml -n multiprompt-sandbox
```

## Manual Deployment

### Build and Push Images

```bash
# Build images
docker build -t gcr.io/$PROJECT_ID/multiprompt-frontend:v1 ./frontend
docker build -t gcr.io/$PROJECT_ID/multiprompt-backend:v1 ./backend

# Push to GCR
docker push gcr.io/$PROJECT_ID/multiprompt-frontend:v1
docker push gcr.io/$PROJECT_ID/multiprompt-backend:v1
```

### Deploy to GKE

```bash
# Create namespace
kubectl create namespace multiprompt-sandbox

# Create secrets
kubectl create secret generic app-secrets \
    --from-literal=gemini-api-key=$GEMINI_API_KEY \
    -n multiprompt-sandbox

# Deploy using Kustomize
kubectl apply -k k8s/overlays/prod

# Check deployment status
kubectl get pods -n multiprompt-sandbox
kubectl get services -n multiprompt-sandbox
kubectl get ingress -n multiprompt-sandbox
```

### Verify Deployment

```bash
# Check pod status
kubectl get pods -n multiprompt-sandbox

# Check logs
kubectl logs -f deployment/prod-backend -n multiprompt-sandbox
kubectl logs -f deployment/prod-frontend -n multiprompt-sandbox

# Port forward for testing
kubectl port-forward service/prod-backend 8000:80 -n multiprompt-sandbox
kubectl port-forward service/prod-frontend 4200:80 -n multiprompt-sandbox
```

## Continuous Deployment

Once GitHub Actions is configured:

1. Push code to `main` branch
2. GitHub Actions will automatically:
   - Run tests
   - Build Docker images
   - Push to Artifact Registry
   - Deploy to GKE

## Rollback

```bash
# View deployment history
kubectl rollout history deployment/prod-backend -n multiprompt-sandbox

# Rollback to previous version
kubectl rollout undo deployment/prod-backend -n multiprompt-sandbox

# Rollback to specific revision
kubectl rollout undo deployment/prod-backend --to-revision=2 -n multiprompt-sandbox
```

## Monitoring

```bash
# View logs
kubectl logs -f deployment/prod-backend -n multiprompt-sandbox

# Describe pod
kubectl describe pod <pod-name> -n multiprompt-sandbox

# Execute commands in pod
kubectl exec -it <pod-name> -n multiprompt-sandbox -- /bin/bash

# View events
kubectl get events -n multiprompt-sandbox --sort-by='.lastTimestamp'
```

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n multiprompt-sandbox
kubectl logs <pod-name> -n multiprompt-sandbox
```

### Image pull errors
```bash
# Verify image exists
gcloud artifacts docker images list us-central1-docker.pkg.dev/$PROJECT_ID/multiprompt-repo

# Check service account permissions
kubectl get serviceaccount -n multiprompt-sandbox
```

### Ingress not working
```bash
kubectl describe ingress -n multiprompt-sandbox
kubectl get events -n multiprompt-sandbox
```

## Cleanup

```bash
# Delete Kubernetes resources
kubectl delete namespace multiprompt-sandbox

# Delete GKE cluster
gcloud container clusters delete multiprompt-cluster --zone=us-central1-a

# Delete Artifact Registry
gcloud artifacts repositories delete multiprompt-repo --location=us-central1
```

## Cost Optimization

1. Use preemptible nodes for non-production
2. Enable cluster autoscaling
3. Set resource limits on pods
4. Use appropriate machine types
5. Clean up unused resources
