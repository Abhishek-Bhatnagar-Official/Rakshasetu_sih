"""
Module 3 - Resource Requirements

Determines the types, minimum quantities, and capabilities
of resources required for an incident.

This module does NOT:
- Select specific resources
- Check resource availability
- Assign resources to incidents
- Calculate routes or travel distance

Those responsibilities belong to later modules.
"""

from typing import Any


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

ALLOWED_RESOURCE_TYPES = {
    "rescue_team",
    "ambulance",
    "boat",
    "medical_team",
}


# ---------------------------------------------------------------------
# Safe normalization helpers
# ---------------------------------------------------------------------

def _safe_int(value: Any) -> int:
    """
    Safely convert a value to a non-negative integer.

    Handles:
        None
        int
        float
        numeric strings
        invalid values

    Invalid values become 0.
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
        except (TypeError, ValueError):
            return 0

    return 0


def _safe_boolean(value: Any) -> bool:
    """
    Safely convert common boolean representations.

    Important:
        bool("false") is True in Python, so normal bool()
        conversion must not be used for external payloads.

    True values:
        True
        1
        "true"
        "1"
        "yes"
        "y"
        "on"

    False values:
        False
        0
        "false"
        "0"
        "no"
        "n"
        "off"
        ""
        None
        "none"
        "null"
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


def _normalize_incident_type(value: Any) -> str:
    """
    Normalize incident type for rule matching.
    """

    if value is None:
        return ""

    return str(value).strip().lower()


# ---------------------------------------------------------------------
# Requirement helper
# ---------------------------------------------------------------------

def _add_requirement(
    requirements: list[dict[str, Any]],
    resource_type: str,
    minimum_count: int,
    capabilities: list[str],
) -> None:
    """
    Add a resource requirement to the list.

    If the same resource type already exists, merge the
    requirement instead of creating a duplicate entry.
    """

    if minimum_count <= 0:
        return

    # Keep capability list clean and deterministic.
    normalized_capabilities = []

    for capability in capabilities:
        if capability is None:
            continue

        normalized = str(capability).strip()

        if normalized and normalized not in normalized_capabilities:
            normalized_capabilities.append(normalized)

    # Check whether this resource type already exists.
    for requirement in requirements:
        if requirement["resource_type"] == resource_type:

            requirement["minimum_count"] += minimum_count

            for capability in normalized_capabilities:
                if (
                    capability
                    not in requirement["required_capabilities"]
                ):
                    requirement["required_capabilities"].append(
                        capability
                    )

            return

    # Add a new requirement.
    requirements.append(
        {
            "resource_type": resource_type,
            "minimum_count": minimum_count,
            "required_capabilities": normalized_capabilities,
        }
    )


# ---------------------------------------------------------------------
# Main resource requirement engine
# ---------------------------------------------------------------------

def determine_resource_requirements(
    incident: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Determine resource requirements for an incident.

    Parameters
    ----------
    incident : dict
        Incident information produced by incident_creator.py.

    Returns
    -------
    list[dict]
        Resource requirements containing:
        - resource_type
        - minimum_count
        - required_capabilities

    Notes
    -----
    This function determines WHAT is required, not WHICH
    specific resources should be assigned.
    """

    if not isinstance(incident, dict):
        raise TypeError(
            "incident must be a dictionary."
        )

    requirements: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # Extract and normalize incident information
    # ---------------------------------------------------------

    incident_type = _normalize_incident_type(
        incident.get("incident_type")
    )

    affected_people = _safe_int(
        incident.get("affected_people")
    )

    injured_people = _safe_int(
        incident.get("injured_people")
    )

    trapped_people = _safe_int(
        incident.get("trapped_people")
    )

    people_trapped = _safe_boolean(
        incident.get("people_trapped")
    )

    medical_emergency = _safe_boolean(
        incident.get("medical_emergency")
    )

    # An explicit trapped count means people are trapped,
    # regardless of the boolean field.
    if trapped_people > 0:
        people_trapped = True

    severity_indicators = incident.get(
        "severity_indicators",
        []
    )

    if not isinstance(severity_indicators, list):
        severity_indicators = []

    # ---------------------------------------------------------
    # 1. Rescue team requirements
    # ---------------------------------------------------------

    rescue_required = (
        people_trapped
        or trapped_people > 0
        or incident_type in {
            "building_collapse",
            "earthquake",
            "landslide",
            "accident",
            "structural_collapse",
            "fire",
            "flood",
        }
    )

    if rescue_required:

        rescue_count = 1

        # Increase rescue teams when many people are trapped.
        if trapped_people >= 10:
            rescue_count = 3

        elif trapped_people >= 5:
            rescue_count = 2

        # Use canonical capabilities expected by Module 4.
        if incident_type == "flood":
            capabilities = ["flood_rescue"]

        elif incident_type == "landslide":
            capabilities = ["landslide_rescue"]

        else:
            capabilities = ["first_aid"]

        _add_requirement(
            requirements,
            "rescue_team",
            rescue_count,
            capabilities,
        )

    # ---------------------------------------------------------
    # 2. Ambulance requirements
    # ---------------------------------------------------------

    ambulance_required = (
        injured_people > 0
        or medical_emergency
    )

    if ambulance_required:

        if injured_people >= 10:
            ambulance_count = 3

        elif injured_people >= 5:
            ambulance_count = 2

        else:
            ambulance_count = 1

        _add_requirement(
            requirements,
            "ambulance",
            ambulance_count,
            ["medical_transport"],
        )

    # ---------------------------------------------------------
    # 3. Medical team requirements
    # ---------------------------------------------------------

    medical_team_required = (
        medical_emergency
        or injured_people > 0
        or affected_people >= 20
    )

    if medical_team_required:

        if injured_people >= 10 or affected_people >= 100:
            medical_team_count = 2

        else:
            medical_team_count = 1

        _add_requirement(
            requirements,
            "medical_team",
            medical_team_count,
            ["medical_response"],
        )

    # ---------------------------------------------------------
    # 4. Boat requirements
    # ---------------------------------------------------------

    flood_related = (
        incident_type in {
            "flood",
            "flooding",
            "waterlogging",
        }
        or "flood" in incident_type
        or "water" in incident_type
    )

    if flood_related:

        boat_count = 1

        if affected_people >= 100:
            boat_count = 3

        elif affected_people >= 50:
            boat_count = 2

        _add_requirement(
            requirements,
            "boat",
            boat_count,
            ["water_rescue"],
        )

    # ---------------------------------------------------------
    # 5. Additional severity-based requirements
    # ---------------------------------------------------------

    severity_text = " ".join(
        str(indicator).strip().lower()
        for indicator in severity_indicators
        if indicator is not None
    )

    if "mass_casualty" in severity_text:

        _add_requirement(
            requirements,
            "medical_team",
            1,
            ["medical_response"],
        )

    # ---------------------------------------------------------
    # 6. Validate generated requirements
    # ---------------------------------------------------------

    for requirement in requirements:

        resource_type = requirement["resource_type"]

        if resource_type not in ALLOWED_RESOURCE_TYPES:
            raise ValueError(
                f"Invalid resource type: {resource_type}"
            )

        minimum_count = requirement["minimum_count"]

        if not isinstance(minimum_count, int):
            raise ValueError(
                "minimum_count must be an integer."
            )

        if minimum_count < 1:
            raise ValueError(
                "minimum_count must be at least 1."
            )

        capabilities = requirement[
            "required_capabilities"
        ]

        if not isinstance(capabilities, list):
            raise ValueError(
                "required_capabilities must be a list."
            )

    return requirements


# ---------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------

__all__ = [
    "ALLOWED_RESOURCE_TYPES",
    "determine_resource_requirements",
]