"""
Module 4 - Data Layer

Contains the initial Assam resource inventory and mock incident data.

This module is responsible for:
- Defining the initial resource inventory
- Defining mock prioritized incidents
- Providing controlled access to the in-memory resource state

This module does NOT:
- Optimize allocations
- Select resources for incidents
- Calculate routes
- Decide incident priority
"""

from copy import deepcopy
from typing import Any


# ---------------------------------------------------------------------
# Initial Assam Resource Inventory
# ---------------------------------------------------------------------

MOCK_RESOURCES = [
    {
        "resource_id": "RT01",
        "resource_type": "rescue_team",
        "name": "Guwahati NDRF Unit 1",
        "latitude": 26.1445,
        "longitude": 91.7362,
        "capabilities": [
            "flood_rescue",
            "first_aid",
        ],
        "capacity": 10,
        "status": "available",
    },
    {
        "resource_id": "RT02",
        "resource_type": "rescue_team",
        "name": "Silchar SDRF Unit 2",
        "latitude": 24.8333,
        "longitude": 92.7789,
        "capabilities": [
            "first_aid",
        ],
        "capacity": 8,
        "status": "available",
    },
    {
        "resource_id": "AMB01",
        "resource_type": "ambulance",
        "name": "Guwahati Medical Response 1",
        "latitude": 26.1800,
        "longitude": 91.7500,
        "capabilities": [
            "medical_transport",
        ],
        "capacity": 2,
        "status": "available",
    },
    {
        "resource_id": "AMB02",
        "resource_type": "ambulance",
        "name": "Dibrugarh Ambulance 2",
        "latitude": 27.4729,
        "longitude": 94.9122,
        "capabilities": [
            "medical_transport",
        ],
        "capacity": 2,
        "status": "assigned",
    },
    {
        "resource_id": "BOAT01",
        "resource_type": "boat",
        "name": "Kaziranga Relief Boat 1",
        "latitude": 26.5775,
        "longitude": 93.1711,
        "capabilities": [
            "water_rescue",
        ],
        "capacity": 6,
        "status": "available",
    },
]


# ---------------------------------------------------------------------
# Runtime Resource State
# ---------------------------------------------------------------------

# Keep the original MOCK_RESOURCES untouched as the reset template.
#
# RESOURCES is the actual in-memory inventory used by the running
# application. Allocation code should mutate this list rather than
# MOCK_RESOURCES.
RESOURCES: list[dict[str, Any]] = deepcopy(
    MOCK_RESOURCES
)


def get_resources() -> list[dict[str, Any]]:
    """
    Return the current runtime resource inventory.

    A deep copy is returned so callers cannot accidentally mutate
    the inventory without going through the data-layer functions.
    """

    return deepcopy(RESOURCES)


def reset_resources() -> list[dict[str, Any]]:
    """
    Reset runtime resources to the original mock inventory.

    Returns the refreshed inventory.
    """

    global RESOURCES

    RESOURCES = deepcopy(
        MOCK_RESOURCES
    )

    return get_resources()


def get_resource_by_id(
    resource_id: str,
) -> dict[str, Any] | None:
    """
    Find a runtime resource by resource ID.

    Returns:
        A copy of the resource if found.
        None otherwise.
    """

    if not isinstance(resource_id, str):
        return None

    normalized_id = resource_id.strip()

    if not normalized_id:
        return None

    for resource in RESOURCES:
        if resource.get("resource_id") == normalized_id:
            return deepcopy(resource)

    return None


def update_resource_status(
    resource_id: str,
    status: str,
) -> bool:
    """
    Update the status of a runtime resource.

    Returns:
        True if the resource was found and updated.
        False otherwise.
    """

    if not isinstance(resource_id, str):
        return False

    if not isinstance(status, str):
        return False

    normalized_id = resource_id.strip()
    normalized_status = status.strip().lower()

    if not normalized_id or not normalized_status:
        return False

    for resource in RESOURCES:

        if resource.get("resource_id") == normalized_id:

            resource["status"] = normalized_status

            return True

    return False


def mark_resources_assigned(
    resource_ids: list[str],
) -> list[str]:
    """
    Mark the supplied resource IDs as assigned.

    Returns:
        IDs that were successfully updated.

    Already-assigned resources remain assigned.
    Unknown IDs are ignored.
    """

    if not isinstance(resource_ids, list):
        return []

    updated_ids: list[str] = []

    for resource_id in resource_ids:

        if not isinstance(resource_id, str):
            continue

        normalized_id = resource_id.strip()

        if not normalized_id:
            continue

        if update_resource_status(
            normalized_id,
            "assigned",
        ):
            if normalized_id not in updated_ids:
                updated_ids.append(normalized_id)

    return updated_ids


def mark_resources_available(
    resource_ids: list[str],
) -> list[str]:
    """
    Mark the supplied resource IDs as available.

    Returns:
        IDs that were successfully updated.
    """

    if not isinstance(resource_ids, list):
        return []

    updated_ids: list[str] = []

    for resource_id in resource_ids:

        if not isinstance(resource_id, str):
            continue

        normalized_id = resource_id.strip()

        if not normalized_id:
            continue

        if update_resource_status(
            normalized_id,
            "available",
        ):
            if normalized_id not in updated_ids:
                updated_ids.append(normalized_id)

    return updated_ids


# ---------------------------------------------------------------------
# Mock Prioritized Incidents
# ---------------------------------------------------------------------

MOCK_INCIDENTS = [
    {
        "incident_id": "I001",
        "latitude": 26.1500,
        "longitude": 91.7400,
        "priority_score": 85,
        "priority_level": "critical",
        "resource_requirements": [
            {
                "resource_type": "rescue_team",
                "minimum_count": 1,
                "required_capabilities": [
                    "flood_rescue",
                ],
            }
        ],
        "allocation_eligible": True,
        "incident_status": "pending_allocation",
    }
]


# ---------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------

__all__ = [
    "MOCK_RESOURCES",
    "RESOURCES",
    "MOCK_INCIDENTS",
    "get_resources",
    "reset_resources",
    "get_resource_by_id",
    "update_resource_status",
    "mark_resources_assigned",
    "mark_resources_available",
]