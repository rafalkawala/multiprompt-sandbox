#!/bin/bash

# Build and push Docker images to Google Container Registry

set -e

# Check if PROJECT_ID is set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set"
    exit 1
fi

PROJECT_ID=$GCP_PROJECT_ID
VERSION=${1:-latest}

echo "Building and pushing images to GCR..."
echo "Project ID: $PROJECT_ID"
echo "Version: $VERSION"

# Build frontend
echo "Building frontend..."
docker build -t gcr.io/$PROJECT_ID/multiprompt-frontend:$VERSION \
             -t gcr.io/$PROJECT_ID/multiprompt-frontend:latest \
             ./frontend

# Build backend
echo "Building backend..."
docker build -t gcr.io/$PROJECT_ID/multiprompt-backend:$VERSION \
             -t gcr.io/$PROJECT_ID/multiprompt-backend:latest \
             ./backend

# Push frontend
echo "Pushing frontend..."
docker push gcr.io/$PROJECT_ID/multiprompt-frontend:$VERSION
docker push gcr.io/$PROJECT_ID/multiprompt-frontend:latest

# Push backend
echo "Pushing backend..."
docker push gcr.io/$PROJECT_ID/multiprompt-backend:$VERSION
docker push gcr.io/$PROJECT_ID/multiprompt-backend:latest

echo "Images pushed successfully!"
echo "Frontend: gcr.io/$PROJECT_ID/multiprompt-frontend:$VERSION"
echo "Backend: gcr.io/$PROJECT_ID/multiprompt-backend:$VERSION"
