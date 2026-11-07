import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datasets import parse_pasted_csv


def test_header_row_skipped():
    timestamps, values = parse_pasted_csv(
        "timestamp,value\n2026-01-01,100\n2026-01-02,101\n"
    )
    assert timestamps == ["2026-01-01", "2026-01-02"]
    assert values == [100.0, 101.0]


def test_no_header_row():
    timestamps, values = parse_pasted_csv("2026-01-01,100\n2026-01-02,101\n")
    assert values == [100.0, 101.0]


def test_blank_lines_ignored():
    _, values = parse_pasted_csv("\n2026-01-01,100\n\n2026-01-02,101\n")
    assert values == [100.0, 101.0]


def test_non_numeric_value_after_first_row_raises():
    # A typo in the middle of pasted data used to silently drop the row;
    # now it fails with the offending line called out.
    with pytest.raises(ValueError, match="line 3.*not a number"):
        parse_pasted_csv(
            "2026-01-01,100\n2026-01-02,101\n2026-01-03,abc\n2026-01-04,103\n"
        )


def test_non_numeric_value_with_header_raises():
    with pytest.raises(ValueError, match="line 3.*not a number"):
        parse_pasted_csv(
            "timestamp,value\n2026-01-01,100\n2026-01-02,xyz\n"
        )


def test_wrong_column_count_raises():
    with pytest.raises(ValueError, match="exactly two columns"):
        parse_pasted_csv("2026-01-01,100,extra\n2026-01-02,101\n")


def test_too_few_rows_raises():
    with pytest.raises(ValueError, match="at least 2 data rows"):
        parse_pasted_csv("timestamp,value\n2026-01-01,100\n")
