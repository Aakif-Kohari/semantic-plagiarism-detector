"""
tests/utils/test_pagination.py
------------------------------
Unit tests for pagination utilities.

Validates PaginationPage dataclass behavior including __repr__, __eq__,
factory methods, and navigation helpers.
"""

import pytest
from src.utils.pagination import PaginationPage


class TestPaginationPageRepr:
    """Test suite for custom __repr__ implementation."""

    def test_repr_with_small_items_list(self):
        """Verify __repr__ shows full list when 3 or fewer items."""
        page = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )

        repr_str = repr(page)
        assert "page=1/2" in repr_str
        assert "items=[1, 2, 3]" in repr_str

    def test_repr_with_large_items_list(self):
        """Verify __repr__ truncates to count when more than 3 items."""
        page = PaginationPage(
            items=[1, 2, 3, 4, 5, 6, 7, 8],
            page=1,
            total_pages=2,
            total_items=15,
            per_page=8,
        )

        repr_str = repr(page)
        assert "page=1/2" in repr_str
        assert "items=8" in repr_str
        # Should NOT contain the full list
        assert "[1, 2, 3, 4, 5, 6, 7, 8]" not in repr_str

    def test_repr_with_empty_items_list(self):
        """Verify __repr__ handles empty items list correctly."""
        page = PaginationPage(
            items=[],
            page=1,
            total_pages=1,
            total_items=0,
            per_page=10,
        )

        repr_str = repr(page)
        assert "page=1/1" in repr_str
        assert "items=[]" in repr_str

    def test_repr_with_exactly_three_items(self):
        """Verify __repr__ shows full list at exactly 3 items (boundary)."""
        page = PaginationPage(
            items=["a", "b", "c"],
            page=2,
            total_pages=3,
            total_items=9,
            per_page=3,
        )

        repr_str = repr(page)
        assert "items=['a', 'b', 'c']" in repr_str

    def test_repr_with_four_items(self):
        """Verify __repr__ truncates at exactly 4 items (boundary)."""
        page = PaginationPage(
            items=["a", "b", "c", "d"],
            page=1,
            total_pages=1,
            total_items=4,
            per_page=10,
        )

        repr_str = repr(page)
        assert "items=4" in repr_str
        assert "['a', 'b', 'c', 'd']" not in repr_str


class TestPaginationPageEq:
    """Test suite for __eq__ implementation."""

    def test_equal_pages_are_equal(self):
        """Verify two identical pages are equal."""
        page1 = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )
        page2 = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )

        assert page1 == page2

    def test_different_items_not_equal(self):
        """Verify pages with different items are not equal."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[4, 5, 6], page=1, total_pages=2, total_items=10, per_page=5
        )

        assert page1 != page2

    def test_different_page_number_not_equal(self):
        """Verify pages with different page numbers are not equal."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[1, 2, 3], page=2, total_pages=2, total_items=10, per_page=5
        )

        assert page1 != page2

    def test_different_total_pages_not_equal(self):
        """Verify pages with different total_pages are not equal."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=3, total_items=10, per_page=5
        )

        assert page1 != page2

    def test_different_total_items_not_equal(self):
        """Verify pages with different total_items are not equal."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=15, per_page=5
        )

        assert page1 != page2

    def test_different_per_page_not_equal(self):
        """Verify pages with different per_page are not equal."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=10
        )

        assert page1 != page2

    def test_not_equal_to_non_pagination_page(self):
        """Verify page is not equal to non-PaginationPage objects."""
        page = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )

        assert page != "not a page"
        assert page != 123
        assert page != {"items": [1, 2, 3]}
        assert page != None

    def test_equal_pages_have_same_hash(self):
        """Verify equal pages have the same hash (for use in sets/dicts)."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )

        assert hash(page1) == hash(page2)

    def test_pages_can_be_used_in_set(self):
        """Verify pages can be added to sets (requires __hash__)."""
        page1 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page2 = PaginationPage(
            items=[1, 2, 3], page=1, total_pages=2, total_items=10, per_page=5
        )
        page3 = PaginationPage(
            items=[4, 5, 6], page=1, total_pages=2, total_items=10, per_page=5
        )

        page_set = {page1, page2, page3}
        assert len(page_set) == 2  # page1 and page2 are duplicates


class TestPaginationPageFactory:
    """Test suite for PaginationPage.create() factory method."""

    def test_create_calculates_total_pages_correctly(self):
        """Verify create() calculates total_pages correctly."""
        page = PaginationPage.create(
            items=[1, 2, 3],
            page=1,
            per_page=10,
            total_items=25,
        )

        assert page.total_pages == 3  # 25 items / 10 per page = 3 pages

    def test_create_handles_exact_division(self):
        """Verify create() handles exact division (no remainder)."""
        page = PaginationPage.create(
            items=[1, 2, 3, 4, 5],
            page=1,
            per_page=5,
            total_items=20,
        )

        assert page.total_pages == 4  # 20 items / 5 per page = 4 pages

    def test_create_handles_empty_results(self):
        """Verify create() returns at least 1 page even with 0 items."""
        page = PaginationPage.create(
            items=[],
            page=1,
            per_page=10,
            total_items=0,
        )

        assert page.total_pages == 1
        assert page.total_items == 0

    def test_create_raises_on_invalid_page(self):
        """Verify create() raises ValueError for page < 1."""
        with pytest.raises(ValueError, match="page must be >= 1"):
            PaginationPage.create(items=[], page=0, per_page=10, total_items=0)

    def test_create_raises_on_invalid_per_page(self):
        """Verify create() raises ValueError for per_page < 1."""
        with pytest.raises(ValueError, match="per_page must be >= 1"):
            PaginationPage.create(items=[], page=1, per_page=0, total_items=0)


class TestPaginationPageNavigation:
    """Test suite for navigation helper methods."""

    def test_has_next_true_when_not_last_page(self):
        """Verify has_next() returns True when not on last page."""
        page = PaginationPage(
            items=[1], page=1, total_pages=3, total_items=10, per_page=5
        )
        assert page.has_next() is True

    def test_has_next_false_on_last_page(self):
        """Verify has_next() returns False on last page."""
        page = PaginationPage(
            items=[1], page=3, total_pages=3, total_items=10, per_page=5
        )
        assert page.has_next() is False

    def test_has_previous_true_when_not_first_page(self):
        """Verify has_previous() returns True when not on first page."""
        page = PaginationPage(
            items=[1], page=2, total_pages=3, total_items=10, per_page=5
        )
        assert page.has_previous() is True

    def test_has_previous_false_on_first_page(self):
        """Verify has_previous() returns False on first page."""
        page = PaginationPage(
            items=[1], page=1, total_pages=3, total_items=10, per_page=5
        )
        assert page.has_previous() is False

    def test_next_page_returns_correct_number(self):
        """Verify next_page() returns page + 1 when available."""
        page = PaginationPage(
            items=[1], page=2, total_pages=5, total_items=10, per_page=5
        )
        assert page.next_page() == 3

    def test_next_page_returns_none_on_last_page(self):
        """Verify next_page() returns None on last page."""
        page = PaginationPage(
            items=[1], page=5, total_pages=5, total_items=10, per_page=5
        )
        assert page.next_page() is None

    def test_previous_page_returns_correct_number(self):
        """Verify previous_page() returns page - 1 when available."""
        page = PaginationPage(
            items=[1], page=3, total_pages=5, total_items=10, per_page=5
        )
        assert page.previous_page() == 2

    def test_previous_page_returns_none_on_first_page(self):
        """Verify previous_page() returns None on first page."""
        page = PaginationPage(
            items=[1], page=1, total_pages=5, total_items=10, per_page=5
        )
        assert page.previous_page() is None


class TestPaginationPageSerialization:
    """Test suite for to_dict() serialization."""

    def test_to_dict_contains_all_fields(self):
        """Verify to_dict() includes all required fields."""
        page = PaginationPage(
            items=[1, 2, 3], page=2, total_pages=5, total_items=20, per_page=5
        )
        result = page.to_dict()

        assert "items" in result
        assert "page" in result
        assert "total_pages" in result
        assert "total_items" in result
        assert "per_page" in result
        assert "has_next" in result
        assert "has_previous" in result
        assert "next_page" in result
        assert "previous_page" in result

    def test_to_dict_values_are_correct(self):
        """Verify to_dict() returns correct values."""
        page = PaginationPage(
            items=[1, 2, 3], page=2, total_pages=5, total_items=20, per_page=5
        )
        result = page.to_dict()

        assert result["items"] == [1, 2, 3]
        assert result["page"] == 2
        assert result["total_pages"] == 5
        assert result["total_items"] == 20
        assert result["per_page"] == 5
        assert result["has_next"] is True
        assert result["has_previous"] is True
        assert result["next_page"] == 3
        assert result["previous_page"] == 1
