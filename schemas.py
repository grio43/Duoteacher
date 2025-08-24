#!/usr/bin/env python3
"""
Standardized schemas for prediction outputs across all tools.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path


@dataclass
class TagPrediction:
    """Single tag prediction."""
    name: str
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "score": round(self.score, 4)}


@dataclass
class ImagePrediction:
    """Prediction result for a single image."""
    image: str  # Path or identifier
    tags: List[TagPrediction]
    processing_time: Optional[float] = None  # in milliseconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "image": self.image,
            "tags": [t.to_dict() for t in self.tags],
            "processing_time": self.processing_time
        }


@dataclass
class RunMetadata:
    """Metadata for a prediction run."""
    top_k: int
    threshold: float
    vocab_sha256: str
    normalize_mean: List[float]
    normalize_std: List[float]
    image_size: int
    patch_size: int
    model_path: Optional[str] = None
    num_tags: Optional[int] = None
    vocab_embedded: bool = True  # Whether vocab came from model metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PredictionOutput:
    """Complete output with metadata and results."""
    metadata: RunMetadata
    results: List[ImagePrediction]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "results": [r.to_dict() for r in self.results]
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, filepath: Path) -> None:
        """Save to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


def compute_vocab_sha256(vocab_path: Optional[Path] = None,
                        vocab_data: Optional[Dict] = None) -> str:
    """Compute SHA256 hash of vocabulary.
    
    Args:
        vocab_path: Path to vocabulary file
        vocab_data: Vocabulary data dict (if already loaded)
    
    Returns:
        SHA256 hash as hex string
    """
    if vocab_data:
        # Hash the vocabulary data directly
        vocab_json = json.dumps(vocab_data, sort_keys=True)
        return hashlib.sha256(vocab_json.encode()).hexdigest()
    elif vocab_path and vocab_path.exists():
        # Hash the file contents
        with open(vocab_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    else:
        return "unknown"


def validate_schema(data: Union[Dict, Path, str]) -> bool:
    """Validate that data conforms to the standard prediction schema.

    Args:
        data: Dictionary, path to JSON file, or JSON string

    Returns:
        True if valid

    Raises:
        ValueError: If schema validation fails with details
    """
    # Load data if needed
    if isinstance(data, (Path, str)):
        if isinstance(data, str) and data.startswith('{'):
            # JSON string
            data = json.loads(data)
        else:
            # File path
            with open(data) as f:
                data = json.load(f)

    # Check top-level structure
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    required_keys = {'metadata', 'results'}
    if not required_keys.issubset(data.keys()):
        raise ValueError(f"Missing required keys: {required_keys - set(data.keys())}")

    # Validate metadata
    metadata = data['metadata']
    required_metadata = {
        'top_k', 'threshold', 'vocab_sha256', 'normalize_mean', 
        'normalize_std', 'image_size', 'patch_size'
    }
    if not required_metadata.issubset(metadata.keys()):
        raise ValueError(f"Missing metadata fields: {required_metadata - set(metadata.keys())}")

    # Validate results
    results = data['results']
    if not isinstance(results, list):
        raise ValueError("Results must be a list")

    for i, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError(f"Result {i} must be a dictionary")

        if 'image' not in result or 'tags' not in result:
            raise ValueError(f"Result {i} missing 'image' or 'tags'")

        if not isinstance(result['tags'], list):
            raise ValueError(f"Result {i} tags must be a list")

        for j, tag in enumerate(result['tags']):
            if not isinstance(tag, dict):
                raise ValueError(f"Result {i} tag {j} must be a dictionary")
            if 'name' not in tag or 'score' not in tag:
                raise ValueError(f"Result {i} tag {j} missing 'name' or 'score'")
            if not isinstance(tag['name'], str):
                raise ValueError(f"Result {i} tag {j} name must be string")
            if not isinstance(tag['score'], (int, float)):
                raise ValueError(f"Result {i} tag {j} score must be numeric")

    return True


# Legacy adapter is in convert_legacy_to_standard() below

