import json
import pytest
from datetime import datetime
from src.utils.json_export import export_to_json

def test_export_to_json_default_date_format():
    """Verify default date format."""
    data = {"timestamp": datetime(2026, 8, 1, 10, 50, 55)}
    result = export_to_json(data)
    parsed = json.loads(result)
    assert parsed["timestamp"] == "2026-08-01T10:50:55Z"

def test_export_to_json_custom_date_format():
    """Verify custom date format."""
    data = {"timestamp": datetime(2026, 8, 1, 10, 50, 55)}
    result = export_to_json(data, date_format="%Y/%m/%d %H:%M")
    parsed = json.loads(result)
    assert parsed["timestamp"] == "2026/08/01 10:50"

def test_export_to_json_multiple_timestamp_fields():
    """Verify multiple timestamp fields."""
    data = [
        {"created_at": datetime(2026, 8, 1, 10, 0, 0)},
        {"updated_at": datetime(2026, 8, 2, 11, 0, 0)}
    ]
    result = export_to_json(data)
    parsed = json.loads(result)
    assert parsed[0]["created_at"] == "2026-08-01T10:00:00Z"
    assert parsed[1]["updated_at"] == "2026-08-02T11:00:00Z"

def test_export_to_json_empty_dataset():
    """Verify empty dataset."""
    assert export_to_json([]) == "[]"
    assert export_to_json({}) == "{}"

def test_export_to_json_datetime_serialization_remains_valid():
    """Verify datetime serialization remains valid for standard json output."""
    data = {"name": "test", "date": datetime(2026, 1, 1, 0, 0, 0)}
    result = export_to_json(data)
    assert '"name": "test"' in result
    assert '"date": "2026-01-01T00:00:00Z"' in result
