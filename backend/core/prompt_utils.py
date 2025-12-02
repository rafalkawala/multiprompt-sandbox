"""
Utility functions for multi-phase prompt chain processing.

Provides variable substitution and validation for prompt chains where
later steps can reference outputs from previous steps using {outputN} syntax.
"""

import re
from typing import Dict, List, Tuple


def extract_variable_references(prompt: str) -> List[int]:
    """
    Extract variable references like {output1}, {output2} from prompt.

    Args:
        prompt: The prompt text to analyze

    Returns:
        Sorted list of step numbers referenced (e.g., [1, 2, 5])

    Example:
        >>> extract_variable_references("Is {output1} correct? And {output2}?")
        [1, 2]
    """
    pattern = r'\{output(\d+)\}'
    matches = re.findall(pattern, prompt)
    return sorted([int(m) for m in matches])


def validate_variable_references(
    prompt: str,
    current_step: int,
    available_outputs: Dict[int, str]
) -> Tuple[bool, str]:
    """
    Validate that all variable references are valid.

    Args:
        prompt: The prompt text to validate
        current_step: The current step number (1-indexed)
        available_outputs: Dict mapping step numbers to their outputs

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, "")
        - If invalid: (False, "description of error")

    Example:
        >>> validate_variable_references(
        ...     "Previous: {output1}",
        ...     step=2,
        ...     available_outputs={1: "yes"}
        ... )
        (True, "")
    """
    refs = extract_variable_references(prompt)

    for ref in refs:
        # Cannot reference future steps or current step
        if ref >= current_step:
            return False, f"Cannot reference {{output{ref}}} from step {current_step}"

        # Cannot reference steps that haven't produced output
        if ref not in available_outputs:
            return False, f"Variable {{output{ref}}} not available (step may have failed)"

    return True, ""


def substitute_variables(
    prompt: str,
    outputs: Dict[int, str]
) -> str:
    """
    Replace {outputN} with actual values from previous steps.

    Args:
        prompt: The prompt template with variables
        outputs: Dict mapping step numbers to their output text

    Returns:
        Prompt with all variables substituted

    Example:
        >>> substitute_variables(
        ...     "Given {output1} and {output2}, what do you see?",
        ...     {1: "yes", 2: "no"}
        ... )
        "Given yes and no, what do you see?"
    """
    result = prompt

    for step_num, output_value in outputs.items():
        # Replace {outputN} with the actual output
        # Use re.escape to handle special regex characters in the output value
        pattern = f'{{{{output{step_num}}}}}'
        result = result.replace(pattern, output_value)

    return result
