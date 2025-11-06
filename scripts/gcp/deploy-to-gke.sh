#!/bin/bash

# Deploy to Google Kubernetes Engine

set -e

# Check environment variables
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable is not set"
    exit 1
fi

if [ -z "$GKE_CLUSTER" ]; then
    GKE_CLUSTER="multiprompt-cluster"
fi

if [ -z "$GKE_ZONE" ]; then
    GKE_ZONE="us-central1-a"
fi

ENVIRONMENT=${1:-prod}

echo "Deploying to GKE..."
echo "Project: $GCP_PROJECT_ID"
echo "Cluster: $GKE_CLUSTER"
echo "Zone: $GKE_ZONE"
echo "Environment: $ENVIRONMENT"

# Get cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials $GKE_CLUSTER \
    --zone $GKE_ZONE \
    --project $GCP_PROJECT_ID

# Create namespace if it doesn't exist
kubectl create namespace multiprompt-sandbox --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."
kubectl apply -k k8s/overlays/$ENVIRONMENT

# Wait for rollout
echo "Waiting for deployments to complete..."
kubectl rollout status deployment/prod-frontend -n multiprompt-sandbox
kubectl rollout status deployment/prod-backend -n multiprompt-sandbox

# Get service information
echo "Deployment complete!"
echo ""
echo "Service information:"
kubectl get services -n multiprompt-sandbox
echo ""
echo "Ingress information:"
kubectl get ingress -n multiprompt-sandbox

echo ""
echo "To view logs:"
echo "  kubectl logs -f deployment/prod-backend -n multiprompt-sandbox"
echo "  kubectl logs -f deployment/prod-frontend -n multiprompt-sandbox"
