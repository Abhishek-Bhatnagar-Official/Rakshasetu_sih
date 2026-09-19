"""
Module 3 - Utility Functions

Contains small reusable helper functions used across
the Incident & Priority Engine.

This module should contain generic utilities only.
Business logic belongs in the appropriate module.
"""

from typing import Any


# ============================================================
# Numeric Utilities
# ============================================================

def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to an integer.

    Parameters
    ----------
    value : Any
        Value to convert.

    default : int
        Value returned if conversion fails.

    Returns
    -------
    int
        Converted integer or default value.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return int(value)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to a float.

    Parameters
    ----------
    value : Any
        Value to convert.

    default : float
        Value returned if conversion fails.

    Returns
    -------
    float
        Converted float or default value.
    """

    if value is None:
        return default

    if isinstance(value, bool):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Restrict a numeric value to a given range.

    Example
    -------
    clamp(120, 0, 100) -> 100
    clamp(-10, 0, 100) -> 0
    """

    return max(minimum, min(value, maximum))


# ============================================================
# Boolean Utilities
# ============================================================

def to_bool(value: Any) -> bool:
    """
    Convert common representations of boolean values
    into a Python bool.

    Examples
    --------
    "true"  -> True
    "yes"   -> True
    "1"     -> True
    "false" -> False
    "no"    -> False
    "0"     -> False
    """

    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "true",
            "yes",
            "y",
            "1",
            "on",
        }:
            return True

        if normalized in {
            "false",
            "no",
            "n",
            "0",
            "off",
            "",
        }:
            return False

    return bool(value)


# ============================================================
# String Utilities
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Convert a value to a normalized string.

    Removes leading/trailing whitespace and converts
    repeated whitespace into a single space.
    """

    if value is None:
        return ""

    text = str(value).strip()

    return " ".join(text.split())


def normalize_incident_type(value: Any) -> str:
    """
    Normalize an incident type for rule matching.

    Example
    -------
    " Building Collapse " -> "building_collapse"
    "BUILDING COLLAPSE"   -> "building_collapse"
    """

    text = normalize_text(value).lower()

    return text.replace(" ", "_").replace("-", "_")


# ============================================================
# List Utilities
# ============================================================

def ensure_list(value: Any) -> list:
    """
    Ensure that a value is represented as a list.

    None -> []
    "flood" -> ["flood"]
    ["flood", "injury"] -> unchanged copy
    """

    if value is None:
        return []

    if isinstance(value, list):
        return list(value)

    if isinstance(value, tuple):
        return list(value)

    return [value]


def unique_list(values: list[Any]) -> list[Any]:
    """
    Return a list containing unique values while preserving
    their original order.
    """

    result = []

    for value in values:
        if value not in result:
            result.append(value)

    return result


# ============================================================
# Coordinate Utilities
# ============================================================

def is_valid_latitude(value: Any) -> bool:
    """
    Check whether a value is a valid latitude.

    Valid range: -90 to 90.
    """

    if isinstance(value, bool):
        return False

    try:
        latitude = float(value)
    except (TypeError, ValueError):
        return False

    return -90 <= latitude <= 90


def is_valid_longitude(value: Any) -> bool:
    """
    Check whether a value is a valid longitude.

    Valid range: -180 to 180.
    """

    if isinstance(value, bool):
        return False

    try:
        longitude = float(value)
    except (TypeError, ValueError):
        return False

    return -180 <= longitude <= 180


def has_valid_coordinates(
    latitude: Any,
    longitude: Any,
) -> bool:
    """
    Check whether latitude and longitude are valid
    geographic coordinates.
    """

    return (
        is_valid_latitude(latitude)
        and is_valid_longitude(longitude)
    )


# ============================================================
# Dictionary Utilities
# ============================================================

def get_positive_count(
    data: dict[str, Any],
    key: str,
) -> int:
    """
    Get a non-negative integer count from a dictionary.

    Invalid, missing, or negative values become 0.
    """

    value = safe_int(data.get(key), 0)

    return max(0, value)


def get_string(
    data: dict[str, Any],
    key: str,
    default: str = "",
) -> str:
    """
    Safely retrieve and normalize a string from a dictionary.
    """

    value = data.get(key)

    if value is None:
        return default

    normalized = normalize_text(value)

    return normalized if normalized else default


# ============================================================
# Priority Utilities
# ============================================================

def priority_level_from_score(
    score: float,
    thresholds: dict[str, float],
) -> str:
    """
    Determine priority level from a score and threshold
    configuration.

    Parameters
    ----------
    score : float
        Priority score.

    thresholds : dict
        Dictionary containing critical, high, medium, low
        thresholds.

    Returns
    -------
    str
        Priority level.
    """

    if score >= thresholds["critical"]:
        return "critical"

    if score >= thresholds["high"]:
        return "high"

    if score >= thresholds["medium"]:
        return "medium"

    return "low"


# ============================================================
# Validation Utilities
# ============================================================

def require_dict(
    value: Any,
    name: str = "value",
) -> None:
    """
    Ensure that a value is a dictionary.
    """

    if not isinstance(value, dict):
        raise TypeError(
            f"{name} must be a dictionary."
        )


def require_list(
    value: Any,
    name: str = "value",
) -> None:
    """
    Ensure that a value is a list.
    """

    if not isinstance(value, list):
        raise TypeError(
            f"{name} must be a list."
        )


def require_non_empty_string(
    value: Any,
    name: str,
) -> None:
    """
    Ensure that a value is a non-empty string.
    """

    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string."
        )

    if not value.strip():
        raise ValueError(
            f"{name} cannot be empty."
        )


# ============================================================
# Exported Functions
# ============================================================

__all__ = [
    # Numeric
    "safe_int",
    "safe_float",
    "clamp",

    # Boolean
    "to_bool",

    # String
    "normalize_text",
    "normalize_incident_type",

    # Lists
    "ensure_list",
    "unique_list",

    # Coordinates
    "is_valid_latitude",
    "is_valid_longitude",
    "has_valid_coordinates",

    # Dictionaries
    "get_positive_count",
    "get_string",

    # Priority
    "priority_level_from_score",

    # Validation
    "require_dict",
    "require_list",
    "require_non_empty_string",
]