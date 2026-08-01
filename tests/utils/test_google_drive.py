import pytest
from src.utils.google_drive import extract_google_drive_folder_id

def test_extract_google_drive_folder_id_valid_id():
    valid_id = "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7"
    assert len(valid_id) == 33
    assert extract_google_drive_folder_id(valid_id) == valid_id

def test_extract_google_drive_folder_id_valid_url():
    valid_id = "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7"
    url = f"https://drive.google.com/drive/folders/{valid_id}"
    assert extract_google_drive_folder_id(url) == valid_id

def test_extract_google_drive_folder_id_valid_url_with_query():
    valid_id = "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7"
    url = f"https://drive.google.com/drive/folders/{valid_id}?usp=sharing"
    assert extract_google_drive_folder_id(url) == valid_id

def test_extract_google_drive_folder_id_malformed_url():
    url = "https://drive.google.com/drive/folders/shortid"
    assert extract_google_drive_folder_id(url) is None

def test_extract_google_drive_folder_id_empty_string():
    assert extract_google_drive_folder_id("") is None

def test_extract_google_drive_folder_id_random_string():
    assert extract_google_drive_folder_id("random_garbage_string_not_an_id") is None

def test_extract_google_drive_folder_id_unsupported_url():
    url = "https://google.com"
    assert extract_google_drive_folder_id(url) is None

def test_extract_google_drive_folder_id_whitespace():
    valid_id = "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7"
    assert extract_google_drive_folder_id(f"  {valid_id}  ") == valid_id
    url = f"  https://drive.google.com/drive/folders/{valid_id}?usp=sharing  "
    assert extract_google_drive_folder_id(url) == valid_id

def test_extract_google_drive_folder_id_invalid_type():
    assert extract_google_drive_folder_id(None) is None
    assert extract_google_drive_folder_id(12345) is None
