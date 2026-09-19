from typing import Any


_incident_counter = 0


def generate_incident_id() -> str:
    """Generate a unique incident ID."""

    global _incident_counter
    _incident_counter += 1

    return f"I{_incident_counter:03d}"


def validate_incident_candidate(
    incident_candidate: dict[str, Any]
) -> None:
    """
    Validate the basic structure of an incident candidate.

    Required fields:
    - source_report_ids
    - incident_type
    """

    if not isinstance(incident_candidate, dict):
        raise TypeError(
            "incident_candidate must be a dictionary."
        )

    required_fields = [
        "source_report_ids",
        "incident_type",
    ]

    for field in required_fields:
        if field not in incident_candidate:
            raise KeyError(
                f"Missing required field: '{field}'"
            )

    source_report_ids = incident_candidate["source_report_ids"]

    if not isinstance(source_report_ids, list):
        raise TypeError(
            "source_report_ids must be a list."
        )

    if not source_report_ids:
        raise ValueError(
            "source_report_ids cannot be empty."
        )

    incident_type = incident_candidate["incident_type"]

    if not isinstance(incident_type, str):
        raise TypeError(
            "incident_type must be a string."
        )

    if not incident_type.strip():
        raise ValueError(
            "incident_type cannot be empty."
        )


def create_incident(
    incident_candidate: dict[str, Any]
) -> dict[str, Any]:
    """
    Create a Module 3 incident from an incident candidate.
    """

    validate_incident_candidate(incident_candidate)

    incident = {
        # Unique incident identifier
        "incident_id": generate_incident_id(),

        # Traceability
        "source_report_ids": list(
            incident_candidate["source_report_ids"]
        ),

        # Basic incident information
        "incident_type": incident_candidate["incident_type"],
        "description": incident_candidate.get("description"),

        # Location information
        "location_text": incident_candidate.get("location_text"),
        "latitude": incident_candidate.get("latitude"),
        "longitude": incident_candidate.get("longitude"),
        "location_status": incident_candidate.get("location_status"),

        # Impact information
        "affected_people": incident_candidate.get("affected_people"),
        "injured_people": incident_candidate.get("injured_people"),
        "people_trapped": incident_candidate.get("people_trapped"),
        "trapped_people": incident_candidate.get("trapped_people"),
        "medical_emergency": incident_candidate.get(
            "medical_emergency"
        ),
        "vulnerable_people": incident_candidate.get(
            "vulnerable_people"
        ),

        # Severity information
        "severity_indicators": list(
            incident_candidate.get(
                "severity_indicators", []
            )
        ),

        "reported_at": incident_candidate.get("reported_at"),

        # Module 3 processing fields
        "priority_score": None,
        "priority_level": None,
        "priority_reasons": [],
        "resource_requirements": [],
        "allocation_eligible": None,

        # Initial incident status
        "incident_status": "pending_allocation",
    }

    return incident


__all__ = [
    "generate_incident_id",
    "validate_incident_candidate",
    "create_incident",
]