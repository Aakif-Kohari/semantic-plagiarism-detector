from src.utils.file_parser import truncate_filename


def test_truncate_filename_short():
    """Verify that filenames shorter than max_len are returned unchanged."""
    assert truncate_filename("short.pdf", max_len=15) == "short.pdf"
    assert truncate_filename("essay.txt", max_len=35) == "essay.txt"


def test_truncate_filename_exact():
    """Verify that filenames exactly equal to max_len are returned unchanged."""
    assert truncate_filename("exact_length.pdf", max_len=16) == "exact_length.pdf"


def test_truncate_filename_long():
    """Verify that long filenames are truncated with ellipsis, keeping length <= max_len."""
    name = "this_is_a_very_long_filename_that_exceeds_the_default_limit.pdf"
    truncated = truncate_filename(name, max_len=35)
    assert len(truncated) == 35
    assert truncated.endswith("...")
    assert truncated == "this_is_a_very_long_filename_tha..."


def test_truncate_filename_custom_max_len():
    """Verify that custom max_len bounds are respected."""
    name = "my_document.docx"
    assert truncate_filename(name, max_len=10) == "my_docu..."
    assert len(truncate_filename(name, max_len=10)) == 10
