# GCP Environment Setup

## Configuration Summary

All environment configuration has been standardized between `deploy-gcp.sh` and `cloudbuild.yaml`.

### Database Configuration
- **Instance**: `mllm-sandbox-db-instance`
- **Database Name**: `mllm_sandbox_db`
- **User**: `mllm_sandbox_user`

### Required Secrets in Secret Manager

Before deployment, create these secrets in your GCP project:

```bash
PROJECT_ID="prompting-sandbox-mvp"

# 1. Database password
echo 'YOUR_DB_PASSWORD' | gcloud secrets create multiprompt-db-password --data-file=- --project=$PROJECT_ID

# 2. Application secret key
openssl rand -base64 32 | gcloud secrets create multiprompt-secret-key --data-file=- --project=$PROJECT_ID

# 3. Google OAuth credentials
echo 'YOUR_CLIENT_ID' | gcloud secrets create google-client-id --data-file=- --project=$PROJECT_ID
echo 'YOUR_CLIENT_SECRET' | gcloud secrets create google-client-secret --data-file=- --project=$PROJECT_ID

# 4. Gemini API key
echo 'YOUR_API_KEY' | gcloud secrets create multiprompt-gemini-api-key --data-file=- --project=$PROJECT_ID

# 5. Admin emails (comma-separated list of emails that get admin role on login)
echo 'admin@example.com' | gcloud secrets create multiprompt-admin-emails --data-file=- --project=$PROJECT_ID
```

### Environment Variables (cloudbuild.yaml)

The backend Cloud Run service receives these environment variables:

| Variable | Description |
|----------|-------------|
| `ENVIRONMENT` | Set to `production` |
| `DB_HOST` | Cloud SQL private IP |
| `DB_PORT` | `5432` |
| `DB_USER` | `multiprompt` |
| `DB_NAME` | `multiprompt` |
| `GCP_PROJECT_ID` | Project ID |
| `FRONTEND_URL` | Frontend Cloud Run URL |
| `GOOGLE_REDIRECT_URI` | Backend OAuth callback URL |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins |

### Secrets Mounted to Cloud Run

| Secret | Secret Manager Name |
|--------|---------------------|
| `DB_PASSWORD` | `multiprompt-db-password` |
| `SECRET_KEY` | `multiprompt-secret-key` |
| `GOOGLE_CLIENT_ID` | `google-client-id` |
| `GOOGLE_CLIENT_SECRET` | `google-client-secret` |
| `GEMINI_API_KEY` | `multiprompt-gemini-api-key` |
| `ADMIN_EMAILS` | `multiprompt-admin-emails` |

## Local Development

For local development, create a `.env` file in the `backend/` directory:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_local_password
DB_NAME=multiprompt

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:4200

# Security
SECRET_KEY=your_dev_secret_key

# Optional
GEMINI_API_KEY=your_api_key
```

## Deployment

### Automated Deployment (Recommended)

Push to the `main` branch triggers automatic deployment via Cloud Build:

```bash
git add .
git commit -m "Your changes"
git push origin main
```

Cloud Build will automatically:
1. Run tests
2. Build container images
3. Retrieve Cloud SQL IP dynamically
4. Deploy to Cloud Run
5. Update environment variables with actual URLs

### Manual Deployment

For manual deployment or first-time setup:

```bash
./scripts/deploy-gcp.sh
```

### First-Time Setup

Before the first deployment:

1. Create all secrets in Secret Manager (see above)
2. Ensure Cloud Build trigger is configured:
   ```bash
   gcloud builds triggers create github \
     --repo-name=MultiPromptSandbox \
     --repo-owner=YOUR_GITHUB_USERNAME \
     --branch-pattern=^main$ \
     --build-config=cloudbuild.yaml \
     --project=prompting-sandbox-mvp
   ```
3. Grant Cloud Build service account permissions:
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe prompting-sandbox-mvp --format='value(projectNumber)')

   # Cloud Run Admin
   gcloud projects add-iam-policy-binding prompting-sandbox-mvp \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/run.admin"

   # Service Account User
   gcloud projects add-iam-policy-binding prompting-sandbox-mvp \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"

   # Secret Manager Accessor
   gcloud projects add-iam-policy-binding prompting-sandbox-mvp \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"

   # Cloud SQL Client
   gcloud projects add-iam-policy-binding prompting-sandbox-mvp \
     --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   ```

## Dynamic Configuration

The `cloudbuild.yaml` uses fully dynamic configuration with no hardcoded values.

### Substitution Variables
All configurable values are defined as substitutions:
```yaml
substitutions:
  _REGION: 'us-central1'
  _DB_INSTANCE: 'mllm-sandbox-db-instance'
  _DB_NAME: 'mllm_sandbox_db'
  _DB_USER: 'mllm_sandbox_user'
  _VPC_CONNECTOR: 'mllm-vpc-connector'
```

Override these when triggering builds:
```bash
gcloud builds submit --substitutions=_REGION=europe-west1,_DB_INSTANCE=my-db
```

### Dynamic Lookups
- **DB_HOST**: Retrieved from Cloud SQL instance at deploy time
- **Cloud Run URLs**: Retrieved from existing services, then updated after deployment

Containers are fully environment-agnostic.

### OAuth Redirect URIs
Remember to add your production OAuth redirect URI to Google Cloud Console:
- `https://YOUR-BACKEND-URL/api/v1/auth/google/callback`

The actual URL is determined dynamically after deployment.
