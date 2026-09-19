"""
Module 3 - Priority Rules

Contains the configuration used by the priority engine.

This file defines:
1. Priority factor weights
2. Priority level thresholds
3. Basic validation for the scoring configuration

The scoring logic itself is implemented in priority_engine.py.
"""


# ============================================================
# Priority Factor Weights
# ============================================================

PRIORITY_WEIGHTS = {
    # People are trapped and may require immediate rescue
    "people_trapped": 30,

    # A medical emergency requires urgent response
    "medical_emergency": 20,

    # Injured people may require immediate medical assistance
    "injuries": 15,

    # Larger affected populations increase incident impact
    "affected_people": 15,

    # Vulnerable people require additional consideration
    "vulnerable_people": 10,

    # Additional severity indicators
    "severity_indicators": 10,
}


# ============================================================
# Priority Level Thresholds
# ============================================================

PRIORITY_THRESHOLDS = {
    # Score >= 80
    "critical": 80,

    # Score >= 60
    "high": 60,

    # Score >= 30
    "medium": 30,

    # Score >= 0
    "low": 0,
}


# ============================================================
# Score Limits
# ============================================================

MIN_PRIORITY_SCORE = 0
MAX_PRIORITY_SCORE = 100


# ============================================================
# Resource Requirement Rules
# ============================================================

# These rules provide configuration values for
# resource_requirements.py.

RESOURCE_REQUIREMENT_RULES = {
    "trapped_people": {
        "rescue_team": {
            "thresholds": {
                0: 1,
                5: 2,
                10: 3,
            },
            "capabilities": [
                "search_and_rescue",
                "trapped_person_extraction",
            ],
        }
    },

    "injured_people": {
        "ambulance": {
            "thresholds": {
                0: 0,
                1: 1,
                5: 2,
                10: 3,
            },
            "capabilities": [
                "patient_transport",
                "emergency_medical_support",
            ]
        }
    },

    "medical_emergency": {
        "medical_team": {
            "minimum_count": 1,
            "capabilities": [
                "first_aid",
                "emergency_medical_care",
            ]
        }
    },

    "flood": {
        "boat": {
            "minimum_count": 1,
            "capabilities": [
                "water_rescue",
                "evacuation",
            ]
        }
    },
}


# ============================================================
# Incident Types Requiring Rescue
# ============================================================

RESCUE_INCIDENT_TYPES = {
    "building_collapse",
    "earthquake",
    "landslide",
    "accident",
    "structural_collapse",
    "fire",
    "flood",
}


# ============================================================
# Flood-Related Incident Types
# ============================================================

FLOOD_INCIDENT_TYPES = {
    "flood",
    "flooding",
    "waterlogging",
}


# ============================================================
# Configuration Validation
# ============================================================

def validate_priority_rules() -> None:
    """
    Validate the priority scoring configuration.

    Raises
    ------
    ValueError
        If the priority weights or thresholds are invalid.
    """

    # --------------------------------------------------------
    # Validate weights
    # --------------------------------------------------------

    for factor, weight in PRIORITY_WEIGHTS.items():

        if not isinstance(weight, (int, float)):
            raise ValueError(
                f"Priority weight for '{factor}' "
                f"must be numeric."
            )

        if weight < 0:
            raise ValueError(
                f"Priority weight for '{factor}' "
                f"cannot be negative."
            )

    # --------------------------------------------------------
    # Validate total possible score
    # --------------------------------------------------------

    total_weight = sum(PRIORITY_WEIGHTS.values())

    if total_weight != MAX_PRIORITY_SCORE:
        raise ValueError(
            f"Priority weights must total "
            f"{MAX_PRIORITY_SCORE}. "
            f"Current total: {total_weight}."
        )

    # --------------------------------------------------------
    # Validate thresholds
    # --------------------------------------------------------

    for level, threshold in PRIORITY_THRESHOLDS.items():

        if not isinstance(threshold, (int, float)):
            raise ValueError(
                f"Threshold for '{level}' must be numeric."
            )

        if not (
            MIN_PRIORITY_SCORE
            <= threshold
            <= MAX_PRIORITY_SCORE
        ):
            raise ValueError(
                f"Threshold for '{level}' must be "
                f"between {MIN_PRIORITY_SCORE} and "
                f"{MAX_PRIORITY_SCORE}."
            )


# ============================================================
# Run Validation When Imported
# ============================================================

validate_priority_rules()


__all__ = [
    "PRIORITY_WEIGHTS",
    "PRIORITY_THRESHOLDS",
    "MIN_PRIORITY_SCORE",
    "MAX_PRIORITY_SCORE",
    "RESOURCE_REQUIREMENT_RULES",
    "RESCUE_INCIDENT_TYPES",
    "FLOOD_INCIDENT_TYPES",
    "validate_priority_rules",
]