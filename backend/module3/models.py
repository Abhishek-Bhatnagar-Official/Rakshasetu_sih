"""
Module 3 - Data Models

Defines the expected data structures used by the
Incident & Priority Engine.

These models are mainly used for type checking and
documentation. The actual runtime data is represented
using normal Python dictionaries.
"""

from typing import Any, Literal, TypedDict


# ============================================================
# Type Definitions
# ============================================================

PriorityLevel = Literal[
    "critical",
    "high",
    "medium",
    "low",
]

IncidentStatus = Literal[
    "pending_allocation",
    "response_assigned",
]

ResourceType = Literal[
    "rescue_team",
    "ambulance",
    "boat",
    "medical_team",
]


# ============================================================
# Incident Candidate
# ============================================================

class IncidentCandidate(TypedDict, total=False):
    """
    Input received from Module 2.

    Module 2 provides incident_candidates to Module 3.
    """

    source_report_ids: list[str]

    incident_type: str
    description: str

    location_text: str
    latitude: float | None
    longitude: float | None
    location_status: str

    affected_people: int
    injured_people: int

    people_trapped: bool
    trapped_people: int

    medical_emergency: bool
    vulnerable_people: Any

    severity_indicators: list[str]

    reported_at: str


# ============================================================
# Priority Factor
# ============================================================

class PriorityFactor(TypedDict):
    """
    Represents one factor contributing to an incident's
    priority score.
    """

    factor: str
    score: int
    reason: str


# ============================================================
# Priority Result
# ============================================================

class PriorityResult(TypedDict):
    """
    Result produced by priority_engine.py.
    """

    priority_score: int
    priority_level: PriorityLevel
    priority_factors: list[PriorityFactor]


# ============================================================
# Resource Requirement
# ============================================================

class ResourceRequirement(TypedDict):
    """
    Represents the resources required for an incident.

    This describes WHAT is needed, not WHICH specific
    resource should be assigned.
    """

    resource_type: ResourceType
    minimum_count: int
    required_capabilities: list[str]


# ============================================================
# Prioritized Incident
# ============================================================

class PrioritizedIncident(TypedDict, total=False):
    """
    Final incident structure produced by Module 3.

    This is the main output passed to the next module.
    """

    # Identification and traceability
    incident_id: str
    source_report_ids: list[str]

    # Incident information
    incident_type: str
    description: str

    # Location information
    location_text: str
    latitude: float | None
    longitude: float | None
    location_status: str

    # Impact information
    affected_people: int | None
    injured_people: int | None
    people_trapped: bool | None
    trapped_people: int | None
    medical_emergency: bool | None
    vulnerable_people: Any

    # Severity
    severity_indicators: list[str]
    reported_at: str | None

    # Priority
    priority_score: int
    priority_level: PriorityLevel
    priority_reasons: list[str]

    # Resource requirements
    resource_requirements: list[ResourceRequirement]

    # Allocation
    allocation_eligible: bool

    # Incident lifecycle
    incident_status: IncidentStatus


# ============================================================
# Module 3 Output
# ============================================================

class Module3Output(TypedDict):
    """
    Top-level output structure of Module 3.
    """

    prioritized_incidents: list[PrioritizedIncident]


# ============================================================
# Utility Type Aliases
# ============================================================

IncidentDict = dict[str, Any]
IncidentCandidateList = list[IncidentCandidate]
PrioritizedIncidentList = list[PrioritizedIncident]


__all__ = [
    "PriorityLevel",
    "IncidentStatus",
    "ResourceType",
    "IncidentCandidate",
    "PriorityFactor",
    "PriorityResult",
    "ResourceRequirement",
    "PrioritizedIncident",
    "Module3Output",
    "IncidentDict",
    "IncidentCandidateList",
    "PrioritizedIncidentList",
]