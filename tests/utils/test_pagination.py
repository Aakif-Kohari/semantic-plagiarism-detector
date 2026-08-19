"""
tests/utils/test_pagination.py
------------------------------
Unit tests for pagination utilities.

Validates PaginationPage dataclass behavior including __repr__, __eq__,
factory methods, and navigation helpers.
"""

import doctest

import pytest

from src.utils import pagination
from src.utils.pagination import PaginationPage, _coerce_integer, paginate_items


class TestPaginationPageReprClassName:
    """Regression tests for the class name in __repr__ (Issue #2200).

    __repr__ built its output from a hardcoded string that misspelled the
    class as "PagnationPage". Every log line, traceback, and debugger frame
    printed a class name that does not exist, so grepping logs for
    "PaginationPage" returned nothing.

    The pre-existing repr tests below all assert on substrings like
    "page=1/2" and "items=[1, 2, 3]" and never look at the class name, which
    is exactly how the typo survived. These tests close that gap.
    """

    def test_repr_starts_with_the_real_class_name(self):
        page = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )

        assert repr(page).startswith("PaginationPage(")

    def test_repr_does_not_contain_the_misspelling(self):
        page = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )

        assert "PagnationPage" not in repr(page)

    def test_repr_class_name_matches_the_type(self):
        """The name must be derived from the type, not hardcoded."""
        page = PaginationPage(
            items=[],
            page=1,
            total_pages=1,
            total_items=0,
            per_page=10,
        )

        assert repr(page).startswith(f"{type(page).__name__}(")

    def test_subclass_reports_its_own_name(self):
        """A hardcoded name would report the base class for any subclass."""

        class AuditLogPage(PaginationPage):
            pass

        page = AuditLogPage(
            items=[1, 2],
            page=1,
            total_pages=1,
            total_items=2,
            per_page=10,
        )

        assert repr(page).startswith("AuditLogPage(")
        assert "PaginationPage(" not in repr(page)

    def test_repr_includes_per_page(self):
        """per_page is a field but was invisible in the repr."""
        page = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )

        assert "per_page=5" in repr(page)

    def test_repr_distinguishes_pages_that_differ_only_by_page_size(self):
        """Without per_page these two rendered identically."""
        first = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )
        second = PaginationPage(
            items=[1, 2, 3],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=50,
        )

        assert repr(first) != repr(second)

    def test_repr_is_exactly_as_documented(self):
        """Pin the full string so the format cannot drift silently."""
        truncated = PaginationPage(
            items=[1, 2, 3, 4, 5],
            page=1,
            total_pages=2,
            total_items=10,
            per_page=5,
        )
        full = PaginationPage(
            items=[1, 2],
            page=1,
            total_pages=1,
            total_items=2,
            per_page=10,
        )

        assert repr(truncated) == "PaginationPage(page=1/2, items=5, per_page=5)"
        assert repr(full) == "PaginationPage(page=1/1, items=[1, 2], per_page=10)"


class TestPaginationModuleDoctests:
    """The __repr__ docstring examples must match real behaviour."""

    def test_docstring_examples_pass(self):
        results = doctest.testmod(pagination, verbose=False)

        assert results.failed == 0, (
            f"{results.failed} of {results.attempted} doctests in "
            "src/utils/pagination.py failed"
        )

    def test_doctests_are_actually_present(self):
        """Guard the guard: testmod passes vacuously with no examples."""
        results = doctest.testmod(pagination, verbose=False)

        assert results.attempted > 0, "expected doctest examples in pagination.py"


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
        # Deliberate `!=` rather than `is not`: this exercises __eq__'s
        # non-PaginationPage branch, which `is not None` would bypass.
        assert page != None  # noqa: E711

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


# --- NEW TESTS ADDED FOR ISSUE #2030 ---

class TestCoerceInteger:
    """Test suite for _coerce_integer helper function."""

    def test_coerce_integer_valid_strings(self):
        """Verify valid number strings are coerced to int."""
        assert _coerce_integer("10", 1) == 10

    def test_coerce_integer_invalid_string(self):
        """Verify invalid strings return the fallback/default."""
        assert _coerce_integer("abc", 1) == 1

    def test_coerce_integer_none(self):
        """Verify None returns the fallback/default."""
        assert _coerce_integer(None, 1) == 1

    def test_coerce_integer_float(self):
        """Verify floats are coerced/truncated to int."""
        assert _coerce_integer(3.14, 1) == 3
        assert _coerce_integer(-2.9, 1) == -2


class TestPaginateItemsBoundaryConditions:
    """Test suite for paginate_items boundary conditions (Issue #2030)."""

    def test_empty_list(self):
        """Verify empty list returns empty list regardless of pagination."""
        assert paginate_items([], page=1, page_size=10) == []

    def test_page_zero(self):
        """Verify page=0 is clamped to 1."""
        items = [1, 2, 3, 4, 5]
        assert paginate_items(items, page=0, page_size=2) == [1, 2]

    def test_page_negative(self):
        """Verify page=-1 is clamped to 1."""
        items = [1, 2, 3, 4, 5]
        assert paginate_items(items, page=-1, page_size=2) == [1, 2]

    def test_page_beyond_range(self):
        """Verify page=9999 is clamped to the last available page."""
        items = [1, 2, 3, 4, 5]
        # 5 items total, page_size=2 means 3 pages. The last page contains just [5].
        assert paginate_items(items, page=9999, page_size=2) == [5]

    def test_page_size_zero(self):
        """Verify page_size=0 is clamped to a minimum valid size (1)."""
        items = [1, 2, 3]
        assert paginate_items(items, page=1, page_size=0) == [1]

    def test_page_size_negative(self):
        """Verify page_size=-5 is clamped to a minimum valid size (1)."""
        items = [1, 2, 3]
        assert paginate_items(items, page=1, page_size=-5) == [1]

    def test_page_string(self):
        """Verify string inputs for page are handled and coerced gracefully."""
        items = [1, 2, 3, 4, 5]
        # "abc" coercion fails, defaults to 1
        assert paginate_items(items, page="abc", page_size=2) == [1, 2]
        