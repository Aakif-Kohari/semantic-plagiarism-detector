"""
tests/utils/test_google_drive.py
---------------------------------
Unit tests for Google Drive utilities.
"""

import sys
import os
# Add src/utils to path to import google_drive module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'utils'))

import google_drive


def test_get_supported_file_extensions():
    """Test that get_supported_file_extensions returns expected list of extensions."""
    extensions = google_drive.get_supported_file_extensions()

    # The returned object is a list
    assert isinstance(extensions, list)

    # The list contains ".pdf"
    assert ".pdf" in extensions

    # The list contains ".docx"
    assert ".docx" in extensions

    # The list is sorted alphabetically
    assert extensions == sorted(extensions)

    # The list contains no duplicate values
    assert len(extensions) == len(set(extensions))
