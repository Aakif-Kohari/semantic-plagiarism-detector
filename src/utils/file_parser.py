"""Utility functions for file handling and name formatting."""


def truncate_filename(name: str, max_len: int = 35) -> str:
    """Truncate filename with ellipsis if it exceeds max_len."""
    if len(name) <= max_len:
        return name
    return name[: max_len - 3] + "..."
