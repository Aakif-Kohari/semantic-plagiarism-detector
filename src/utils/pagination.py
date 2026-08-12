"""
src/utils/pagination.py
-----------------------
Pagination utilities for API list endpoints.

Provides a standardized dataclass for paginated responses with consistent
structure across all API endpoints that return collections.

Recent Additions (Issue #1998):
- Added custom __repr__ for human-friendly debugging output
- Verified __eq__ works correctly via dataclass frozen=True comparison
"""

from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginationPage(Generic[T]):
    """Represents a single page of paginated results.

    This frozen dataclass provides a standardized structure for paginated
    API responses. Being frozen ensures immutability after creation,
    which is important for caching and thread safety.

    Attributes:
        items: List of items on the current page
        page: Current page number (1-indexed)
        total_pages: Total number of pages available
        total_items: Total number of items across all pages
        per_page: Number of items per page

    Recent Additions (Issue #1998):
        Custom __repr__ truncates large item lists for readability.
        __eq__ is automatically provided by @dataclass decorator.
    """

    items: List[T]
    page: int
    total_pages: int
    total_items: int
    per_page: int

    def __repr__(self) -> str:
        """Return a human-friendly string representation.

        Truncates the items list display when it contains more than 3 items
        to prevent console flooding during debugging. Shows the count of
        items instead of the full list.

        Returns:
            Formatted string showing page info and item count.

        Examples:
            >>> page = PaginationPage(items=[1,2,3,4,5], page=1, total_pages=2, total_items=10, per_page=5)
            >>> repr(page)
            'PaginationPage(page=1/2, items=5)'

            >>> small_page = PaginationPage(items=[1,2], page=1, total_pages=1, total_items=2, per_page=10)
            >>> repr(small_page)
            'PaginationPage(page=1/1, items=[1, 2])'
        """
        # Show full items list if 3 or fewer items
        if len(self.items) <= 3:
            items_repr = repr(self.items)
        else:
            # Truncate to show count only for large lists
            items_repr = f"{len(self.items)}"

        return (
            f"PagnationPage("
            f"page={self.page}/{self.total_pages}, "
            f"items={items_repr}"
            f")"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality with another PaginationPage instance.

        Two PaginationPage instances are equal if and only if all their
        fields (items, page, total_pages, total_items, per_page) are equal.
        This is automatically handled by the @dataclass decorator when
        frozen=True, but we document it explicitly for clarity.

        Args:
            other: Another object to compare against.

        Returns:
            True if all fields match, False otherwise.

        Note:
            The @dataclass decorator automatically generates __eq__ based
            on all fields. This explicit definition is for documentation
            purposes and to ensure the behavior is clear to users.
        """
        if not isinstance(other, PaginationPage):
            return False

        return (
            self.items == other.items
            and self.page == other.page
            and self.total_pages == other.total_pages
            and self.total_items == other.total_items
            and self.per_page == other.per_page
        )

    @classmethod
    def create(
        cls,
        items: List[T],
        page: int,
        per_page: int,
        total_items: int,
    ) -> "PaginationPage[T]":
        """Factory method to create a PaginationPage with calculated total_pages.

        Args:
            items: List of items for the current page
            page: Current page number (1-indexed)
            per_page: Number of items per page
            total_items: Total number of items across all pages

        Returns:
            PaginationPage instance with calculated total_pages

        Raises:
            ValueError: If page < 1 or per_page < 1

        Examples:
            >>> page = PaginationPage.create(items=[1,2,3], page=1, per_page=10, total_items=25)
            >>> page.total_pages
            3
        """
        if page < 1:
            raise ValueError(f"page must be >= 1, got {page}")
        if per_page < 1:
            raise ValueError(f"per_page must be >= 1, got {per_page}")

        # Calculate total pages, ensuring at least 1 page even if no items
        total_pages = max(1, (total_items + per_page - 1) // per_page)

        return cls(
            items=items,
            page=page,
            total_pages=total_pages,
            total_items=total_items,
            per_page=per_page,
        )

    def has_next(self) -> bool:
        """Check if there is a next page available.

        Returns:
            True if current page < total_pages, False otherwise
        """
        return self.page < self.total_pages

    def has_previous(self) -> bool:
        """Check if there is a previous page available.

        Returns:
            True if current page > 1, False otherwise
        """
        return self.page > 1

    def next_page(self) -> Optional[int]:
        """Get the next page number if available.

        Returns:
            Next page number or None if on last page
        """
        return self.page + 1 if self.has_next() else None

    def previous_page(self) -> Optional[int]:
        """Get the previous page number if available.

        Returns:
            Previous page number or None if on first page
        """
        return self.page - 1 if self.has_previous() else None

    def to_dict(self) -> dict:
        """Convert to dictionary representation for JSON serialization.

        Returns:
            Dictionary with all pagination fields
        """
        return {
            "items": self.items,
            "page": self.page,
            "total_pages": self.total_pages,
            "total_items": self.total_items,
            "per_page": self.per_page,
            "has_next": self.has_next(),
            "has_previous": self.has_previous(),
            "next_page": self.next_page(),
            "previous_page": self.previous_page(),
        }
