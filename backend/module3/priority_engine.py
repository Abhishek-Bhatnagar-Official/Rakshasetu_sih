"""
Module 3 - Incident & Priority Engine
======================================

priority_engine.py

Responsible for calculating the operational priority of an incident.

Input:
    incident: dict

Output:
    {
        "priority_score": int,
        "priority_level": str,
        "priority_factors": list[dict]
    }

Priority score:
    0 - 100

Priority levels:
    critical
    high
    medium
    low

Design:
    Explainable weighted/rule-based scoring.

This file does NOT:
    - create incidents
    - cluster reports
    - generate resource assignments
    - calculate routes
    - perform optimization
    - manage the dashboard
"""

from typing import Any

from .rules import PRIORITY_WEIGHTS, PRIORITY_THRESHOLDS


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

MIN_PRIORITY_SCORE = 0
MAX_PRIORITY_SCORE = 100


# ---------------------------------------------------------------------
# Safe normalization helpers
# ---------------------------------------------------------------------

def _safe_non_negative_int(value: Any) -> int:
    """
    Convert a value into a non-negative integer.

    Handles:
        - None
        - integers
        - floats
        - numeric strings
        - invalid strings

    Invalid values become 0.

    Important:
        bool is handled explicitly because bool is a subclass of int.
    """

    if value is None:
        return 0

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return max(0, value)

    if isinstance(value, float):
        if value != value:  # NaN
            return 0
        return max(0, int(value))

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return 0

        try:
            return max(0, int(float(value)))
        except (ValueError, TypeError):
            return 0

    return 0


def _safe_boolean(value: Any) -> bool:
    """
    Convert common boolean representations safely.

    This deliberately avoids:

        bool("false") == True

    Supported true values:
        True
        1
        "true"
        "1"
        "yes"
        "y"
        "on"

    Supported false values:
        False
        0
        "false"
        "0"
        "no"
        "n"
        "off"
        ""
        None
    """

    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "true",
            "1",
            "yes",
            "y",
            "on",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
            "n",
            "off",
            "",
            "none",
            "null",
        }:
            return False

    return False


# ---------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------

def extract_priority_features(
    incident: dict[str, Any]
) -> dict[str, Any]:
    """
    Extract and normalize information relevant to priority calculation.

    Parameters
    ----------
    incident : dict[str, Any]
        Standardized incident created by incident_creator.py.

    Returns
    -------
    dict[str, Any]
        Normalized priority-related features.
    """

    affected_people = _safe_non_negative_int(
        incident.get("affected_people")
    )

    injured_people = _safe_non_negative_int(
        incident.get("injured_people")
    )

    trapped_people = _safe_non_negative_int(
        incident.get("trapped_people")
    )

    people_trapped = _safe_boolean(
        incident.get("people_trapped")
    )

    medical_emergency = _safe_boolean(
        incident.get("medical_emergency")
    )

    vulnerable_people = incident.get(
        "vulnerable_people"
    )

    severity_indicators = incident.get(
        "severity_indicators",
        []
    )

    if not isinstance(severity_indicators, list):
        severity_indicators = []

    # Normalize indicator strings and remove empty values.
    normalized_indicators = []

    for indicator in severity_indicators:
        if indicator is None:
            continue

        text = str(indicator).strip()

        if text:
            normalized_indicators.append(text)

    # If an explicit trapped count exists, the incident is necessarily
    # considered to contain trapped people.
    if trapped_people > 0:
        people_trapped = True

    return {
        "affected_people": affected_people,
        "injured_people": injured_people,
        "trapped_people": trapped_people,
        "people_trapped": people_trapped,
        "medical_emergency": medical_emergency,
        "vulnerable_people": vulnerable_people,
        "severity_indicators": normalized_indicators,
    }


# ---------------------------------------------------------------------
# Individual scoring functions
# ---------------------------------------------------------------------

def score_people_trapped(
    features: dict[str, Any]
) -> tuple[int, str | None]:
    """
    Calculate score contribution from trapped people.
    """

    if (
        not features["people_trapped"]
        and features["trapped_people"] <= 0
    ):
        return 0, None

    weight = PRIORITY_WEIGHTS["people_trapped"]

    if features["trapped_people"] > 0:
        reason = (
            f'{features["trapped_people"]} people reported trapped'
        )
    else:
        reason = "people reported trapped"

    return weight, reason


def score_medical_emergency(
    features: dict[str, Any]
) -> tuple[int, str | None]:
    """
    Calculate score contribution from a medical emergency.
    """

    if not features["medical_emergency"]:
        return 0, None

    weight = PRIORITY_WEIGHTS["medical_emergency"]

    return weight, "medical emergency reported"


def score_injuries(
    features: dict[str, Any]
) -> tuple[int, str | None]:
    """
    Calculate score contribution from reported injuries.
    """

    injured_people = features["injured_people"]

    if injured_people <= 0:
        return 0, None

    weight = PRIORITY_WEIGHTS["injuries"]

    if injured_people == 1:
        reason = "1 injured person reported"
    else:
        reason = (
            f"{injured_people} injured people reported"
        )

    return weight, reason


def score_affected_population(
    features: dict[str, Any]
) -> tuple[int, str | None]:
    """
    Calculate score contribution from the affected population.

    The contribution increases according to the number of people
    affected, while remaining capped at the configured weight.
    """

    affected_people = features["affected_people"]

    if affected_people <= 0:
        return 0, None

    maximum_weight = PRIORITY_WEIGHTS["affected_people"]

    if affected_people >= 100:
        contribution = maximum_weight

    elif affected_people >= 50:
        contribution = round(
            maximum_weight * 0.75
        )

    elif affected_people >= 20:
        contribution = round(
            maximum_weight * 0.50
        )

    elif affected_people >= 10:
        contribution = round(
            maximum_weight * 0.25
        )

    else:
        contribution = 0

    if contribution == 0:
        return 0, None

    reason = (
        f"{affected_people} people affected"
    )

    return contribution, reason


def score_vulnerable_people(
    features: dict[str, Any]
) -> tuple[int, str | None]:
    """
    Calculate score contribution when vulnerable people
    are reported.
    """

    vulnerable_people = features["vulnerable_people"]

    if vulnerable_people is None:
        return 0, None

    if isinstance(vulnerable_people, bool):
        has_vulnerable_people = vulnerable_people

    elif isinstance(vulnerable_people, int):
        has_vulnerable_people = vulnerable_people > 0

    elif isinstance(vulnerable_people, list):
        has_vulnerable_people = len(vulnerable_people) > 0

    else:
        has_vulnerable_people = _safe_boolean(
            vulnerable_people
        )

    if not has_vulnerable_people:
        return 0, None

    weight = PRIORITY_WEIGHTS["vulnerable_people"]

    return weight, "vulnerable people reported"


def score_severity_indicators(
    features: dict[str, Any]
) -> tuple[int, str | None]:
    """
    Calculate score contribution from additional severity indicators.

    Only indicators that are not already directly represented by
    another scoring factor are considered here.
    """

    indicators = features["severity_indicators"]

    if not indicators:
        return 0, None

    weight = PRIORITY_WEIGHTS["severity_indicators"]

    known_indicators = {
        "people_trapped",
        "injuries_reported",
        "medical_emergency",
    }

    additional_indicators = [
        indicator
        for indicator in indicators
        if indicator not in known_indicators
    ]

    if not additional_indicators:
        return 0, None

    contribution = weight

    reason = (
        "additional severity indicators: "
        + ", ".join(additional_indicators)
    )

    return contribution, reason


# ---------------------------------------------------------------------
# Priority score calculation
# ---------------------------------------------------------------------

def calculate_priority_score(
    incident: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    """
    Calculate the total priority score.

    Parameters
    ----------
    incident : dict[str, Any]
        Standardized incident.

    Returns
    -------
    tuple[int, list[dict[str, Any]]]
        Total score and the factors contributing to it.
    """

    features = extract_priority_features(incident)

    factors: list[dict[str, Any]] = []

    scoring_functions = [
        (
            "people_trapped",
            score_people_trapped,
        ),
        (
            "medical_emergency",
            score_medical_emergency,
        ),
        (
            "injuries",
            score_injuries,
        ),
        (
            "affected_people",
            score_affected_population,
        ),
        (
            "vulnerable_people",
            score_vulnerable_people,
        ),
        (
            "severity_indicators",
            score_severity_indicators,
        ),
    ]

    total_score = 0

    for factor_name, scoring_function in scoring_functions:

        contribution, reason = scoring_function(
            features
        )

        if contribution <= 0:
            continue

        factors.append(
            {
                "factor": factor_name,
                "score": contribution,
                "reason": reason,
            }
        )

        total_score += contribution

    total_score = max(
        MIN_PRIORITY_SCORE,
        min(total_score, MAX_PRIORITY_SCORE),
    )

    return total_score, factors


# ---------------------------------------------------------------------
# Priority level assignment
# ---------------------------------------------------------------------

def assign_priority_level(
    priority_score: int
) -> str:
    """
    Convert a numeric priority score into a priority level.

    Parameters
    ----------
    priority_score : int
        Score between 0 and 100.

    Returns
    -------
    str
        critical, high, medium, or low.
    """

    if not isinstance(priority_score, (int, float)):
        raise TypeError(
            "priority_score must be numeric."
        )

    if not MIN_PRIORITY_SCORE <= priority_score <= MAX_PRIORITY_SCORE:
        raise ValueError(
            "priority_score must be between 0 and 100."
        )

    if priority_score >= PRIORITY_THRESHOLDS["critical"]:
        return "critical"

    if priority_score >= PRIORITY_THRESHOLDS["high"]:
        return "high"

    if priority_score >= PRIORITY_THRESHOLDS["medium"]:
        return "medium"

    return "low"


# ---------------------------------------------------------------------
# Main priority function
# ---------------------------------------------------------------------

def calculate_priority(
    incident: dict[str, Any]
) -> dict[str, Any]:
    """
    Calculate the complete priority information for an incident.

    Parameters
    ----------
    incident : dict[str, Any]
        Standardized incident.

    Returns
    -------
    dict[str, Any]
        Priority result containing:

        {
            "priority_score": int,
            "priority_level": str,
            "priority_factors": list[dict]
        }
    """

    if not isinstance(incident, dict):
        raise TypeError(
            "incident must be a dictionary."
        )

    priority_score, priority_factors = (
        calculate_priority_score(incident)
    )

    priority_level = assign_priority_level(
        priority_score
    )

    return {
        "priority_score": priority_score,
        "priority_level": priority_level,
        "priority_factors": priority_factors,
    }


# ---------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------

__all__ = [
    "extract_priority_features",
    "calculate_priority_score",
    "assign_priority_level",
    "calculate_priority",
]