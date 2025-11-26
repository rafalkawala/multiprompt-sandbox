#!/usr/bin/env python
"""Validate cloudbuild.yaml syntax"""
import yaml
import sys

try:
    with open('cloudbuild.yaml', 'r') as f:
        yaml.safe_load(f)
    print('✓ YAML syntax is valid')
    sys.exit(0)
except yaml.YAMLError as e:
    print('✗ YAML syntax error:')
    print(e)
    sys.exit(1)
except FileNotFoundError:
    print('✗ cloudbuild.yaml not found')
    sys.exit(1)
