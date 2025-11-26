#!/bin/bash
# Validate cloudbuild.yaml syntax

echo "Validating cloudbuild.yaml..."

# Check if yamllint is available
if command -v yamllint &> /dev/null; then
    echo "Running yamllint..."
    yamllint cloudbuild.yaml
else
    echo "yamllint not found, using Python YAML parser..."
    conda run -n multiprompt-sandbox python validate_yaml.py
fi

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "✓ cloudbuild.yaml is valid"
else
    echo "✗ cloudbuild.yaml has errors"
    exit 1
fi
