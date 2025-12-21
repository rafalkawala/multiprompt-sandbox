from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ImageEvalData:
    id: str
    dataset_id: str
    filename: str
    storage_path: str
    ground_truth: Optional[Dict[str, Any]]
