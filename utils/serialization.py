# -*- coding: utf-8 -*-
"""
maya_faceit.utils.serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Serialization utilities for saving/loading data.
"""

import json
import pickle
import hashlib
import os
from typing import Any, Dict, Optional, Union
from pathlib import Path


class SerializationUtils:
    """Utilities for serializing Python objects."""

    @staticmethod
    def to_json(data: Any, pretty: bool = True) -> str:
        """Serialize object to JSON string."""
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    @staticmethod
    def from_json(json_str: str) -> Any:
        """Deserialize object from JSON string."""
        return json.loads(json_str)

    @staticmethod
    def save_json(data: Any, filepath: Union[str, Path], pretty: bool = True) -> bool:
        """Save data as JSON to a file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, default=str)
                else:
                    json.dump(data, f, default=str)
            return True
        except Exception:
            return False

    @staticmethod
    def load_json(filepath: Union[str, Path]) -> Optional[Any]:
        """Load JSON from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def to_pickle(data: Any) -> bytes:
        """Serialize to pickle bytes."""
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def from_pickle(data: bytes) -> Any:
        """Deserialize from pickle bytes."""
        return pickle.loads(data)

    @staticmethod
    def save_pickle(data: Any, filepath: Union[str, Path]) -> bool:
        """Save data as pickle to a file."""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            return True
        except Exception:
            return False

    @staticmethod
    def load_pickle(filepath: Union[str, Path]) -> Optional[Any]:
        """Load pickle from a file."""
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None

    @staticmethod
    def compute_hash(data: Any, algorithm: str = "md5") -> str:
        """Compute a hash of any Python object."""
        import hashlib
        hash_func = hashlib.new(algorithm)
        json_str = SerializationUtils.to_json(data, pretty=False)
        hash_func.update(json_str.encode('utf-8'))
        return hash_func.hexdigest()