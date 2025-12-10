import json
import sys
import os

def validate_pricing_config(config, model_id):
    required = ["mode", "input_price_per_1m", "output_price_per_1m", "image_price_mode"]
    for field in required:
        if field not in config:
            print(f"Error: Model '{model_id}' missing pricing field: {field}")
            return False
    return True

def validate_models(file_path):
    print(f"Validating {file_path}...")
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format: {e}")
        return False
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return False

    if not isinstance(data, list):
        print("Error: Root element must be a list of model objects.")
        return False

    required_fields = [
        "id", "provider", "model_name", "display_name", 
        "description", "endpoint", "auth_type", "pricing_config"
    ]

    valid = True
    ids = set()

    for idx, model in enumerate(data):
        # Check required fields
        for field in required_fields:
            if field not in model:
                print(f"Error: Item {idx} missing required field '{field}'")
                valid = False
        
        # Check ID uniqueness
        if "id" in model:
            if model["id"] in ids:
                print(f"Error: Duplicate ID found: {model['id']}")
                valid = False
            ids.add(model["id"])

        # Check pricing config
        if "pricing_config" in model:
            if not validate_pricing_config(model["pricing_config"], model.get("id", f"item-{idx}")):
                valid = False

    if valid:
        print("Validation Successful! All configurations are valid.")
        return True
    else:
        print("Validation Failed.")
        return False

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "../config/models.json")
    if not validate_models(config_path):
        sys.exit(1)
