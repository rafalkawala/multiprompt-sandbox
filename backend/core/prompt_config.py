"""
Prompt configuration loader
Loads system prompts from config/prompts.yaml
"""
import os
import yaml
from typing import Dict, Optional

_prompts: Dict[str, str] = {}
_loaded = False

def load_prompts():
    """Load prompts from config file"""
    global _prompts, _loaded

    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'prompts.yaml')

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            _prompts = config.get('system_prompts', {})
            _prompts['default'] = config.get('default', 'Answer the question based on the image.')
            _loaded = True
    except Exception as e:
        print(f"Warning: Could not load prompts config: {e}")
        # Fallback defaults
        _prompts = {
            'binary': 'Reply only true or false, nothing else.',
            'multiple_choice': 'Reply only with one of these values: {options}',
            'text': 'Reply as short as you can with classification of what you see.',
            'count': 'Reply only with a number that is a count.',
            'default': 'Answer the question based on the image.'
        }
        _loaded = True

def get_system_prompt(question_type: str, options: Optional[list] = None) -> str:
    """
    Get system prompt for a question type

    Args:
        question_type: binary, multiple_choice, text, or count
        options: List of options for multiple_choice type

    Returns:
        System prompt string
    """
    if not _loaded:
        load_prompts()

    prompt = _prompts.get(question_type, _prompts.get('default', ''))

    # Replace {options} placeholder for multiple choice
    if question_type == 'multiple_choice' and options:
        options_str = ', '.join(options)
        prompt = prompt.replace('{options}', options_str)

    return prompt.strip()

# Load on import
load_prompts()
