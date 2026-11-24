"""Tests for ``src.addition``.

Run them from the repository root with:

    python -m pytest -v
"""

import pytest

from addition import add


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (1, 2, 3),
        (1, -1, 0),
        (0, 0, 0),
        (-5, -7, -12),
        (2.5, 0.5, 3.0),
    ],
)
def test_add(a: int | float, b: int | float, expected: int | float) -> None:
    assert add(a, b) == expected
