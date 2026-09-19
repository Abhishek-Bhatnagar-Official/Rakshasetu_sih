from typing import Any

from .incident_creator import create_incident
from .priority_engine import calculate_priority
from .priority_explainer import explain_priority
from .resource_requirements import determine_resource_requirements
from .eligibility import determine_allocation_eligibility


# -------------------------------------------------------------------
# Initial incident state
# -------------------------------------------------------------------

INITIAL_INCIDENT_STATUS = "pending_allocation"


# -------------------------------------------------------------------
# Module 3 pipeline
# -------------------------------------------------------------------

def process_incidents(
    incident_candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Process Module 2 incident candidates through the complete
    Module 3 pipeline.

    Pipeline:

        Module 2 candidate
              ↓
        Create incident
              ↓
        Calculate priority
              ↓
        Explain priority
              ↓
        Determine resource requirements
              ↓
        Determine allocation eligibility
              ↓
        Set initial incident status
              ↓
        Module 3 incident

    Important:
        Module 3 does NOT perform resource allocation.
        Allocation is handled downstream by the orchestration
        and optimization layers.
    """

    if not isinstance(
        incident_candidates,
        list
    ):
        raise TypeError(
            "incident_candidates must be a list."
        )

    prioritized_incidents = []

    for candidate in incident_candidates:

        # -----------------------------------------------------------
        # Validate input candidate
        # -----------------------------------------------------------

        if not isinstance(
            candidate,
            dict
        ):
            raise TypeError(
                "Each incident candidate must be a dictionary."
            )

        # -----------------------------------------------------------
        # 1. Create incident
        # -----------------------------------------------------------

        incident = create_incident(
            candidate
        )

        if not isinstance(
            incident,
            dict
        ):
            raise ValueError(
                "create_incident() must return a dictionary."
            )

        # -----------------------------------------------------------
        # 2. Calculate priority
        # -----------------------------------------------------------

        priority_result = calculate_priority(
            incident
        )

        if not isinstance(
            priority_result,
            dict
        ):
            raise ValueError(
                "calculate_priority() must return a dictionary."
            )

        if (
            "priority_score"
            not in priority_result
            or "priority_level"
            not in priority_result
        ):
            raise ValueError(
                "Priority result must contain "
                "'priority_score' and 'priority_level'."
            )

        incident["priority_score"] = (
            priority_result[
                "priority_score"
            ]
        )

        incident["priority_level"] = (
            priority_result[
                "priority_level"
            ]
        )

        # -----------------------------------------------------------
        # 3. Generate priority explanation
        # -----------------------------------------------------------

        incident["priority_reasons"] = (
            explain_priority(
                incident,
                priority_result
            )
        )

        # -----------------------------------------------------------
        # 4. Determine resource requirements
        # -----------------------------------------------------------

        resource_requirements = (
            determine_resource_requirements(
                incident
            )
        )

        if resource_requirements is None:
            resource_requirements = []

        incident["resource_requirements"] = (
            resource_requirements
        )

        # -----------------------------------------------------------
        # 5. Determine allocation eligibility
        # -----------------------------------------------------------

        incident["allocation_eligible"] = (
            determine_allocation_eligibility(
                incident
            )
        )

        # -----------------------------------------------------------
        # 6. Initialize incident status
        # -----------------------------------------------------------

        incident["incident_status"] = (
            INITIAL_INCIDENT_STATUS
        )

        # -----------------------------------------------------------
        # 7. Preserve Module 2 source traceability
        # -----------------------------------------------------------

        # Module 2 provides the source_report_ids that allow
        # downstream layers/dashboard to trace a consolidated
        # incident back to its citizen reports.
        if (
            "source_report_ids"
            not in incident
        ):
            incident["source_report_ids"] = (
                candidate.get(
                    "source_report_ids",
                    []
                )
            )

        prioritized_incidents.append(
            incident
        )

    return prioritized_incidents


# -------------------------------------------------------------------
# Single-incident convenience wrapper
# -------------------------------------------------------------------

def process_single_incident(
    incident_candidate: dict[str, Any]
) -> dict[str, Any]:
    """
    Process one Module 2 incident candidate.

    Convenience wrapper around process_incidents().
    """

    if not isinstance(
        incident_candidate,
        dict
    ):
        raise TypeError(
            "incident_candidate must be a dictionary."
        )

    results = process_incidents(
        [
            incident_candidate
        ]
    )

    if not results:
        raise ValueError(
            "Module 3 produced no incident."
        )

    return results[0]


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

__all__ = [
    "process_incidents",
    "process_single_incident",
]