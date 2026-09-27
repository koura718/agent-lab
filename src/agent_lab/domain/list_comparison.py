"""Deterministic, read-only list comparison with strict input validation."""

from typing import TypedDict

MAX_ITEMS = 1000
MAX_ITEM_LENGTH = 256


class ComparisonInputError(ValueError):
    """Invalid comparison input; messages never contain supplied values."""


class ComparisonResult(TypedDict):
    same: list[str]
    source_only: list[str]
    baseline_only: list[str]


def _validate_items(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ComparisonInputError(f"{field} must be a list of strings.")
    if len(value) > MAX_ITEMS:
        raise ComparisonInputError(f"{field} must contain at most {MAX_ITEMS} items.")
    for item in value:
        if not isinstance(item, str) or not 1 <= len(item) <= MAX_ITEM_LENGTH:
            raise ComparisonInputError(
                f"{field} items must be strings of 1..{MAX_ITEM_LENGTH} characters."
            )
    return value


def compare_lists(source: list[str], baseline: list[str]) -> ComparisonResult:
    """Compare unique values; preserve whitespace, case and Unicode spelling.

    Runtime validation also rejects non-list/non-string inputs. Limits apply
    before deduplication. Inputs are never mutated and output is sorted.
    """
    source_set = set(_validate_items(source, "source"))
    baseline_set = set(_validate_items(baseline, "baseline"))
    return {
        "same": sorted(source_set & baseline_set),
        "source_only": sorted(source_set - baseline_set),
        "baseline_only": sorted(baseline_set - source_set),
    }
