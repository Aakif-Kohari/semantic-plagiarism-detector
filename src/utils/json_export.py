import json
from datetime import datetime
from typing import Any

def export_to_json(data: Any, date_format: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """
    Exports data to a JSON string.
    Datetime objects are serialized using the provided date_format.
    """
    def default_serializer(obj: Any) -> Any:
        if isinstance(obj, datetime):
            # If default format is unchanged, but we are asked to use strftime
            # We use strftime with the date_format
            return obj.strftime(date_format)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(data, default=default_serializer)
