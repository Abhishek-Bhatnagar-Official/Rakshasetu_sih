from typing import Any
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.module4_engine.data import MOCK_RESOURCES
from backend.orchestration.orchestrator import Orchestrator
from backend.module2.module2 import process_reports
from backend.module3.processor import process_incidents


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="RakshaSetu Dashboard API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# In-memory application state
# ============================================================

INCIDENTS: list[dict[str, Any]] = []

# Raw reports are retained so Module 2 can compare a newly
# submitted report with previously submitted reports.
#
# This is intentionally separate from the 120-second
# optimization batching performed by the Orchestrator.
RAW_REPORTS: list[dict[str, Any]] = []

# Maps every source report ID to the consolidated incident ID
# that currently contains that report.
#
# Example:
#
# R001 -> I001
# R002 -> I001
# R003 -> I001
#
# This prevents duplicate reports from creating multiple
# Module 3 incidents and multiple allocations.
REPORT_TO_INCIDENT_ID: dict[str, str] = {}

# Protect the report/incident reconciliation state when
# multiple HTTP requests arrive close together.
STATE_LOCK = Lock()

# Keep the dashboard's own resource inventory independent
# from the orchestrator's internal list.
RESOURCES: list[dict[str, Any]] = [
    dict(resource)
    for resource in MOCK_RESOURCES
]

ALLOCATION_PLANS: dict[str, dict[str, Any]] = {}

ALLOCATION_ACTIONS: dict[str, str] = {}


# ============================================================
# Orchestrator
# ============================================================

ORCHESTRATOR = Orchestrator(
    resources=RESOURCES
)


# ============================================================
# Request models
# ============================================================


class AllocationActionRequest(BaseModel):
    incident_id: str
    action: str
    modified_resources: list[dict[str, Any]] | None = None


# ============================================================
# Helper functions
# ============================================================


def _resource_summary() -> list[dict[str, Any]]:
    """
    Convert detailed resource inventory into the aggregated
    structure expected by the dashboard.
    """

    grouped: dict[str, dict[str, int]] = {}

    for resource in RESOURCES:

        resource_type = resource.get("resource_type")

        if not resource_type:
            continue

        if resource_type not in grouped:
            grouped[resource_type] = {
                "total": 0,
                "available": 0,
                "assigned": 0,
                "unavailable": 0,
            }

        grouped[resource_type]["total"] += 1

        status = resource.get("status")

        if status == "available":
            grouped[resource_type]["available"] += 1

        elif status == "assigned":
            grouped[resource_type]["assigned"] += 1

        elif status == "unavailable":
            grouped[resource_type]["unavailable"] += 1

    display_names = {
        "rescue_team": "Rescue Teams",
        "ambulance": "Ambulances",
        "boat": "Boats",
        "medical_team": "Medical Teams",
    }

    return [
        {
            "resource_type": display_names.get(
                resource_type,
                resource_type,
            ),
            **counts,
        }
        for resource_type, counts in grouped.items()
    ]


def _incident_status(
    incident: dict[str, Any],
) -> str:

    incident_id = incident["incident_id"]

    if incident_id in ALLOCATION_ACTIONS:

        action = ALLOCATION_ACTIONS[incident_id]

        if action == "approve":
            return "response_assigned"

        if action in {"reject", "modify"}:
            return "pending_allocation"

    return incident.get(
        "incident_status",
        "pending_allocation",
    )


def _dashboard_incident(
    incident: dict[str, Any],
) -> dict[str, Any]:

    return {
        "incident_id": incident["incident_id"],

        "incident_type": incident.get(
            "incident_type",
            "other",
        ),

        "location": incident.get(
            "location_text",
            incident.get(
                "location",
                "Unknown",
            ),
        ),

        "latitude": incident.get("latitude"),

        "longitude": incident.get("longitude"),

        "priority_level": incident.get(
            "priority_level",
            "low",
        ),

        "priority_score": incident.get(
            "priority_score",
            0,
        ),

        "status": _incident_status(incident),

        "reported_at": incident.get("reported_at"),
    }


def _dashboard_detail(
    incident: dict[str, Any],
) -> dict[str, Any]:

    return {
        **_dashboard_incident(incident),

        "description": incident.get("description"),

        "affected_people": incident.get(
            "affected_people"
        ),

        "injured_people": incident.get(
            "injured_people"
        ),

        "trapped_people": incident.get(
            "trapped_people"
        ),

        "severity_indicators": incident.get(
            "severity_indicators",
            [],
        ),

        "priority_reasons": incident.get(
            "priority_reasons",
            [],
        ),

        "source_report_ids": incident.get(
            "source_report_ids",
            [],
        ),
    }


# ============================================================
# Report / Incident reconciliation helpers
# ============================================================


def _source_report_ids(
    candidate: dict[str, Any],
) -> set[str]:
    """
    Return the source report IDs belonging to an incident
    candidate.
    """

    return {
        str(report_id)
        for report_id in candidate.get(
            "source_report_ids",
            [],
        )
        if report_id is not None
    }


def _find_existing_incident_id(
    candidate: dict[str, Any],
) -> str | None:
    """
    Determine whether a Module 2 candidate already belongs
    to an incident known by the application.

    Any overlap between source_report_ids and the
    REPORT_TO_INCIDENT_ID mapping means that the candidate
    represents an already-known real-world incident.

    Example:

        Existing:
            R001 -> I001
            R002 -> I001

        New candidate:
            [R001, R002, R004]

        Result:
            I001
    """

    for report_id in _source_report_ids(candidate):

        incident_id = REPORT_TO_INCIDENT_ID.get(
            report_id
        )

        if incident_id:
            return incident_id

    return None


def _register_source_reports(
    incident_id: str,
    candidate: dict[str, Any],
) -> None:
    """
    Associate every source report in a consolidated
    candidate with the incident ID.
    """

    for report_id in _source_report_ids(candidate):

        REPORT_TO_INCIDENT_ID[
            report_id
        ] = incident_id


def _merge_existing_incident(
    existing: dict[str, Any],
    updated: dict[str, Any],
) -> dict[str, Any]:
    """
    Update an existing incident using the latest consolidated
    Module 3 representation while preserving its stable
    incident ID and current allocation/action state.

    This is used when a newly submitted report is clustered
    with an already-known incident.

    IMPORTANT:
    We do not submit the updated duplicate cluster to the
    orchestrator again. This prevents duplicate resource
    allocations for the same real-world incident.
    """

    incident_id = existing["incident_id"]

    merged = dict(updated)

    merged["incident_id"] = incident_id

    # Preserve any existing allocation/action state.
    if "incident_status" not in merged:
        merged["incident_status"] = existing.get(
            "incident_status",
            "pending_allocation",
        )

    return merged


def _store_incident(
    incident: dict[str, Any],
) -> None:
    """
    Store or update an incident by incident ID.
    """

    incident_id = incident.get("incident_id")

    if not incident_id:
        return

    existing_index = next(
        (
            index
            for index, existing
            in enumerate(INCIDENTS)
            if existing.get("incident_id") == incident_id
        ),
        None,
    )

    if existing_index is None:
        INCIDENTS.append(incident)
    else:
        INCIDENTS[existing_index] = incident


def _store_new_or_updated_incident(
    incident: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """
    Store a Module 3 incident while preserving stable identity
    when the candidate belongs to an existing source-report
    cluster.

    Returns:
        (incident, is_existing_incident)
    """

    existing_incident_id = (
        _find_existing_incident_id(candidate)
    )

    if existing_incident_id is None:

        _store_incident(incident)

        _register_source_reports(
            incident["incident_id"],
            candidate,
        )

        return incident, False

    existing_incident = next(
        (
            existing
            for existing in INCIDENTS
            if existing.get("incident_id")
            == existing_incident_id
        ),
        None,
    )

    if existing_incident is None:

        incident["incident_id"] = (
            existing_incident_id
        )

        _store_incident(incident)

        _register_source_reports(
            existing_incident_id,
            candidate,
        )

        return incident, True

    updated_incident = _merge_existing_incident(
        existing_incident,
        incident,
    )

    _store_incident(
        updated_incident
    )

    _register_source_reports(
        existing_incident_id,
        candidate,
    )

    return updated_incident, True


# ============================================================
# Orchestrator → Dashboard synchronization
# ============================================================


def _sync_latest_orchestration_result() -> None:
    """
    Synchronize the dashboard state with the latest result
    produced by the orchestrator.

    This is important because the orchestrator may complete
    its 120-second batching window asynchronously.
    """

    result = ORCHESTRATOR.get_last_result()

    plan = ORCHESTRATOR.get_last_allocation_plan()

    if isinstance(result, dict):

        try:
            update_dashboard_from_orchestrator(
                result
            )

        except (TypeError, ValueError):
            pass

    if isinstance(plan, dict):

        _store_allocation_plan(
            plan
        )


def _dashboard_allocation(
    incident_id: str,
) -> dict[str, Any]:

    _sync_latest_orchestration_result()

    plan = ALLOCATION_PLANS.get(incident_id)

    if plan is None:

        latest_plan = (
            ORCHESTRATOR.get_last_allocation_plan()
        )

        if isinstance(latest_plan, dict):

            _store_allocation_plan(
                latest_plan
            )

            plan = ALLOCATION_PLANS.get(
                incident_id
            )

    if plan is None:

        return {
            "incident_id": incident_id,
            "allocation_status": "pending_approval",
            "recommended_resources": [],
            "reason": [
                "No allocation plan available",
            ],
        }

    assignments = [
        assignment
        for assignment in plan.get("assignments", [])
        if assignment.get("incident_id") == incident_id
    ]

    recommended_resources = []

    for assignment in assignments:

        recommended_resources.append(
            {
                "resource_id": assignment.get(
                    "resource_id"
                ),

                "resource_type": assignment.get(
                    "resource_type"
                ),

                "eta_minutes": assignment.get(
                    "travel_time_min"
                ),

                "distance_km": assignment.get(
                    "distance_km"
                ),
            }
        )

    reasons: list[str] = []

    for assignment in assignments:

        for reason in assignment.get(
            "reasons",
            [],
        ):

            if reason not in reasons:
                reasons.append(reason)

    unserved = [
        requirement
        for requirement in plan.get(
            "unserved_requirements",
            [],
        )
        if requirement.get("incident_id") == incident_id
    ]

    for requirement in unserved:

        reason = requirement.get("reason")

        if reason:

            message = (
                f"Unserved: "
                f"{requirement.get('resource_type')} "
                f"x{requirement.get('required_count')} "
                f"- {reason}"
            )

            if message not in reasons:
                reasons.append(message)

    action = ALLOCATION_ACTIONS.get(
        incident_id
    )

    if action == "approve":
        status = "approved"

    elif action == "reject":
        status = "rejected"

    elif action == "modify":
        status = "modified"

    else:
        status = "pending_approval"

    return {
        "incident_id": incident_id,
        "allocation_status": status,
        "recommended_resources": recommended_resources,
        "reason": reasons,
        "plan_id": plan.get("plan_id"),
        "plan_status": plan.get("status"),
        "generated_at": plan.get("generated_at"),
    }


# ============================================================
# Optimizer result storage
# ============================================================


def _store_allocation_plan(
    plan: dict[str, Any],
) -> None:

    if not isinstance(plan, dict):
        return

    affected_incident_ids = set()

    for assignment in plan.get(
        "assignments",
        [],
    ):

        incident_id = assignment.get(
            "incident_id"
        )

        if incident_id:
            affected_incident_ids.add(
                incident_id
            )

    for requirement in plan.get(
        "unserved_requirements",
        [],
    ):

        incident_id = requirement.get(
            "incident_id"
        )

        if incident_id:
            affected_incident_ids.add(
                incident_id
            )

    for incident_id in affected_incident_ids:

        ALLOCATION_PLANS[
            incident_id
        ] = plan


def update_dashboard_from_orchestrator(
    orchestration_result: dict[str, Any],
) -> None:
    """
    Receive a result from the orchestration layer and update
    dashboard state.

    The Orchestrator owns the live resource inventory.
    """

    if not isinstance(
        orchestration_result,
        dict,
    ):
        raise TypeError(
            "orchestration_result must be a dictionary."
        )

    optimization_input = (
        orchestration_result.get(
            "optimization_input"
        )
    )

    if not isinstance(
        optimization_input,
        dict,
    ):
        raise ValueError(
            "Orchestration result does not contain "
            "valid optimization_input."
        )

    incidents = optimization_input.get(
        "incidents",
        [],
    )

    allocation_plan = (
        orchestration_result.get(
            "allocation_plan"
        )
    )

    if not isinstance(
        allocation_plan,
        dict,
    ):
        allocation_plan = (
            ORCHESTRATOR.get_last_allocation_plan()
        )

    if not isinstance(
        allocation_plan,
        dict,
    ):
        raise ValueError(
            "Allocation plan is not available."
        )

    if isinstance(
        incidents,
        list,
    ):

        for incident in incidents:

            if isinstance(
                incident,
                dict,
            ):

                _store_incident(
                    incident
                )

    _store_allocation_plan(
        allocation_plan
    )


# ============================================================
# Dashboard API
# ============================================================


@app.get("/dashboard/summary")
def get_summary() -> dict[str, int]:

    return {
        "total_reported_incidents": len(
            INCIDENTS
        ),

        "critical_incidents": sum(
            1
            for incident in INCIDENTS
            if incident.get(
                "priority_level"
            ) == "critical"
        ),

        "high_priority_incidents": sum(
            1
            for incident in INCIDENTS
            if incident.get(
                "priority_level"
            ) == "high"
        ),

        "medium_priority_incidents": sum(
            1
            for incident in INCIDENTS
            if incident.get(
                "priority_level"
            ) == "medium"
        ),

        "low_priority_incidents": sum(
            1
            for incident in INCIDENTS
            if incident.get(
                "priority_level"
            ) == "low"
        ),
    }


@app.get("/dashboard/incidents")
def get_incidents() -> dict[
    str,
    list[dict[str, Any]],
]:

    _sync_latest_orchestration_result()

    return {
        "incidents": [
            _dashboard_incident(
                incident
            )
            for incident in INCIDENTS
        ]
    }


@app.get("/dashboard/incidents/{incident_id}")
def get_incident(
    incident_id: str,
) -> dict[str, Any]:

    _sync_latest_orchestration_result()

    for incident in INCIDENTS:

        if incident["incident_id"] == incident_id:

            return _dashboard_detail(
                incident
            )

    raise HTTPException(
        status_code=404,
        detail="Incident not found",
    )


@app.get("/dashboard/resources")
def get_resources() -> dict[
    str,
    list[dict[str, Any]],
]:

    _sync_latest_orchestration_result()

    return {
        "resources": _resource_summary()
    }


@app.get("/dashboard/allocations/{incident_id}")
def get_allocation(
    incident_id: str,
) -> dict[str, Any]:

    if not any(
        incident["incident_id"] == incident_id
        for incident in INCIDENTS
    ):

        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return _dashboard_allocation(
        incident_id
    )


@app.post("/dashboard/allocations/action")
def allocation_action(
    request: AllocationActionRequest,
) -> dict[str, Any]:

    allowed_actions = {
        "approve",
        "modify",
        "reject",
    }

    if request.action not in allowed_actions:

        raise HTTPException(
            status_code=400,
            detail=(
                "action must be one of: "
                "approve, modify, reject"
            ),
        )

    if not any(
        incident["incident_id"]
        == request.incident_id
        for incident in INCIDENTS
    ):

        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    _sync_latest_orchestration_result()

    ALLOCATION_ACTIONS[
        request.incident_id
    ] = request.action

    if (
        request.action == "modify"
        and request.modified_resources is not None
    ):

        existing_plan = ALLOCATION_PLANS.get(
            request.incident_id
        )

        if existing_plan is not None:

            modified_plan = dict(
                existing_plan
            )

            modified_plan[
                "modified_resources"
            ] = request.modified_resources

            ALLOCATION_PLANS[
                request.incident_id
            ] = modified_plan

    return _dashboard_allocation(
        request.incident_id
    )


# ============================================================
# Orchestration endpoints
# ============================================================


@app.post("/dashboard/orchestration/submit")
def submit_to_orchestrator(
    incident: dict[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        incident,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail="incident must be a dictionary",
        )

    try:

        result = ORCHESTRATOR.submit_incident(
            incident
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    _store_incident(
        incident
    )

    if result is not None:

        try:

            update_dashboard_from_orchestrator(
                result
            )

        except ValueError:

            plan = (
                ORCHESTRATOR.get_last_allocation_plan()
            )

            if isinstance(
                plan,
                dict,
            ):

                _store_allocation_plan(
                    plan
                )

        return {
            "status": "optimized",
            "orchestration_result": result,
            "allocation_plan": (
                ORCHESTRATOR
                .get_last_allocation_plan()
            ),
        }

    return {
        "status": "collecting",
        "message": (
            "Incident accepted into the "
            "120-second concurrency window."
        ),
        "incident_id": incident.get(
            "incident_id"
        ),
    }


@app.post("/dashboard/orchestration/flush")
def flush_orchestrator() -> dict[str, Any]:

    try:

        result = ORCHESTRATOR.flush()

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result is None:

        return {
            "status": "empty",
            "message": "No pending incidents.",
        }

    plan = (
        ORCHESTRATOR.get_last_allocation_plan()
    )

    if isinstance(
        plan,
        dict,
    ):

        _store_allocation_plan(
            plan
        )

    try:

        update_dashboard_from_orchestrator(
            result
        )

    except ValueError:
        pass

    return {
        "status": "optimized",
        "orchestration_result": result,
        "allocation_plan": plan,
    }


@app.get("/dashboard/orchestration/status")
def orchestration_status() -> dict[str, Any]:

    _sync_latest_orchestration_result()

    result = (
        ORCHESTRATOR.get_last_result()
    )

    plan = (
        ORCHESTRATOR.get_last_allocation_plan()
    )

    return {
        "has_result": result is not None,
        "has_allocation_plan": plan is not None,
        "orchestration_result": result,
        "allocation_plan": plan,
    }


# ============================================================
# Module 1 → Module 2 → Module 3 bridge
# ============================================================


@app.post("/dashboard/module2/submit")
def submit_module1_reports(
    raw_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Receive raw incident reports from the Module 1 frontend.

    Reports are retained server-side and Module 2 is run
    against the accumulated report set.

    This allows duplicate reports submitted through separate
    HTTP requests to be clustered together.

    IMPORTANT:
    This report accumulation is separate from the
    Orchestrator's 120-second optimization batching.

    Pipeline:

        Module 1 frontend
            ↓
        accumulated raw reports
            ↓
        Module 2
            ↓
        duplicate clustering
            ↓
        Incident candidates
            ↓
        Module 3
            ↓
        Orchestrator
            ↓
        Module 4
            ↓
        Dashboard
    """

    if not isinstance(
        raw_reports,
        list,
    ):
        raise HTTPException(
            status_code=400,
            detail="raw_reports must be a list",
        )

    if not raw_reports:
        raise HTTPException(
            status_code=400,
            detail="At least one report is required",
        )

    for report in raw_reports:

        if not isinstance(
            report,
            dict,
        ):
            raise HTTPException(
                status_code=400,
                detail="Each report must be a dictionary",
            )

    with STATE_LOCK:

        # ----------------------------------------------------
        # 0. Add new reports to the Module 2 report store
        # ----------------------------------------------------

        existing_report_ids = {
            str(
                report.get("report_id")
            )
            for report in RAW_REPORTS
            if report.get("report_id") is not None
        }

        newly_added_reports = []

        for report in raw_reports:

            report_id = report.get(
                "report_id"
            )

            if report_id is not None:

                report_id = str(
                    report_id
                )

                if report_id in existing_report_ids:
                    continue

            report_copy = dict(
                report
            )

            RAW_REPORTS.append(
                report_copy
            )

            newly_added_reports.append(
                report_copy
            )

            if report_id is not None:
                existing_report_ids.add(
                    report_id
                )

        if not newly_added_reports:

            return {
                "status": "success",
                "report_count": len(
                    raw_reports
                ),
                "new_report_count": 0,
                "incident_candidate_count": 0,
                "prioritized_incident_count": 0,
                "incident_candidates": [],
                "prioritized_incidents": [],
                "results": [],
                "message": (
                    "All submitted report IDs were "
                    "already processed."
                ),
            }

        # ----------------------------------------------------
        # 1. Module 2
        #
        # Run clustering against the complete accumulated
        # report set.
        # ----------------------------------------------------

        try:

            incident_candidates = process_reports(
                list(RAW_REPORTS)
            )

        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:

            # Do not leave the state permanently polluted by
            # a report that could not be processed.
            for report in newly_added_reports:

                if report in RAW_REPORTS:
                    RAW_REPORTS.remove(
                        report
                    )

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        # ----------------------------------------------------
        # 2. Only candidates touched by newly submitted
        #    reports need to be considered for this request.
        # ----------------------------------------------------

        new_report_ids = {
            str(
                report.get("report_id")
            )
            for report in newly_added_reports
            if report.get("report_id") is not None
        }

        affected_candidates = []

        for candidate in incident_candidates:

            candidate_report_ids = (
                _source_report_ids(
                    candidate
                )
            )

            if candidate_report_ids.intersection(
                new_report_ids
            ):

                affected_candidates.append(
                    candidate
                )

        # ----------------------------------------------------
        # 3. Module 3
        #
        # Process affected candidates only.
        # ----------------------------------------------------

        try:

            prioritized_incidents = process_incidents(
                affected_candidates
            )

        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        # ----------------------------------------------------
        # 4. Reconcile Module 3 incidents with previously
        #    known source-report clusters.
        # ----------------------------------------------------

        results = []

        for candidate, processed_incident in zip(
            affected_candidates,
            prioritized_incidents,
        ):

            incident, existing_incident = (
                _store_new_or_updated_incident(
                    processed_incident,
                    candidate,
                )
            )

            incident_id = incident.get(
                "incident_id"
            )

            if not incident_id:
                continue

            # ------------------------------------------------
            # Existing cluster:
            #
            # The new report belongs to a real-world incident
            # that has already been submitted to the
            # orchestrator.
            #
            # Do NOT allocate resources again.
            # ------------------------------------------------

            if existing_incident:

                results.append(
                    {
                        "incident_id": incident_id,
                        "status": (
                            "duplicate_cluster_updated"
                        ),
                        "message": (
                            "Report matched an existing "
                            "incident cluster. Existing "
                            "allocation was preserved."
                        ),
                    }
                )

                continue

            # ------------------------------------------------
            # New incident:
            #
            # Submit it normally to the orchestrator.
            # Critical incidents are optimized immediately;
            # other priorities enter the 120-second window.
            # ------------------------------------------------

            try:

                orchestration_result = (
                    ORCHESTRATOR.submit_incident(
                        incident
                    )
                )

            except (
                TypeError,
                ValueError,
            ) as exc:

                raise HTTPException(
                    status_code=400,
                    detail=str(exc),
                )

            if orchestration_result is not None:

                try:

                    update_dashboard_from_orchestrator(
                        orchestration_result
                    )

                except ValueError:

                    plan = (
                        ORCHESTRATOR
                        .get_last_allocation_plan()
                    )

                    if isinstance(
                        plan,
                        dict,
                    ):

                        _store_allocation_plan(
                            plan
                        )

                results.append(
                    {
                        "incident_id": incident_id,
                        "status": "optimized",
                        "orchestration_result": (
                            orchestration_result
                        ),
                        "allocation_plan": (
                            ORCHESTRATOR
                            .get_last_allocation_plan()
                        ),
                    }
                )

            else:

                results.append(
                    {
                        "incident_id": incident_id,
                        "status": "collecting",
                        "message": (
                            "Incident accepted into the "
                            "120-second concurrency window."
                        ),
                    }
                )

        return {
            "status": "success",

            "report_count": len(
                raw_reports
            ),

            "new_report_count": len(
                newly_added_reports
            ),

            "accumulated_report_count": len(
                RAW_REPORTS
            ),

            "incident_candidate_count": len(
                affected_candidates
            ),

            "prioritized_incident_count": len(
                prioritized_incidents
            ),

            "incident_candidates": (
                affected_candidates
            ),

            "prioritized_incidents": (
                prioritized_incidents
            ),

            "results": results,
        }


# ============================================================
# Module 3 → Orchestration bridge
# ============================================================


@app.post("/dashboard/module3/submit")
def submit_module3_incidents(
    incident_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Receive Module 2 incident candidates, process them through
    Module 3, and send prioritized incidents into orchestration.
    """

    if not isinstance(
        incident_candidates,
        list,
    ):
        raise HTTPException(
            status_code=400,
            detail="incident_candidates must be a list",
        )

    try:

        prioritized_incidents = process_incidents(
            incident_candidates
        )

    except (
        TypeError,
        ValueError,
        KeyError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    results = []

    for incident in prioritized_incidents:

        incident_id = incident.get(
            "incident_id"
        )

        if not incident_id:
            continue

        _store_incident(
            incident
        )

        try:

            orchestration_result = (
                ORCHESTRATOR.submit_incident(
                    incident
                )
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        if orchestration_result is not None:

            try:

                update_dashboard_from_orchestrator(
                    orchestration_result
                )

            except ValueError:

                plan = (
                    ORCHESTRATOR
                    .get_last_allocation_plan()
                )

                if isinstance(
                    plan,
                    dict,
                ):

                    _store_allocation_plan(
                        plan
                    )

            results.append(
                {
                    "incident_id": incident_id,
                    "status": "optimized",
                    "orchestration_result": (
                        orchestration_result
                    ),
                    "allocation_plan": (
                        ORCHESTRATOR
                        .get_last_allocation_plan()
                    ),
                }
            )

        else:

            results.append(
                {
                    "incident_id": incident_id,
                    "status": "collecting",
                    "message": (
                        "Incident accepted into the "
                        "120-second concurrency window."
                    ),
                }
            )

    return {
        "status": "success",
        "incident_count": len(
            prioritized_incidents
        ),
        "prioritized_incidents": (
            prioritized_incidents
        ),
        "results": results,
    }


# ============================================================
# Development/Test endpoint
# ============================================================


@app.post("/dashboard/test/run-optimizer")
def run_test_optimizer(
    incidents: list[dict[str, Any]],
) -> dict[str, Any]:

    if not isinstance(
        incidents,
        list,
    ):
        raise HTTPException(
            status_code=400,
            detail="incidents must be a list",
        )

    # Clear incident/report/action/plan state.
    INCIDENTS.clear()
    RAW_REPORTS.clear()
    REPORT_TO_INCIDENT_ID.clear()
    ALLOCATION_PLANS.clear()
    ALLOCATION_ACTIONS.clear()

    # Rebuild the resource inventory from the original mock
    # data so every development/test run starts clean.
    RESOURCES.clear()
    RESOURCES.extend(
        dict(resource)
        for resource in MOCK_RESOURCES
    )

    global ORCHESTRATOR

    ORCHESTRATOR = Orchestrator(
        resources=RESOURCES
    )

    immediate_results = []

    for incident in incidents:

        try:

            result = (
                ORCHESTRATOR.submit_incident(
                    incident
                )
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        _store_incident(
            incident
        )

        if result is not None:

            immediate_results.append(
                result
            )

            plan = (
                ORCHESTRATOR
                .get_last_allocation_plan()
            )

            if isinstance(
                plan,
                dict,
            ):

                _store_allocation_plan(
                    plan
                )

    flushed_result = (
        ORCHESTRATOR.flush()
    )

    if flushed_result is not None:

        plan = (
            ORCHESTRATOR
            .get_last_allocation_plan()
        )

        if isinstance(
            plan,
            dict,
        ):

            _store_allocation_plan(
                plan
            )

        immediate_results.append(
            flushed_result
        )

    final_plan = (
        ORCHESTRATOR
        .get_last_allocation_plan()
    )

    return {
        "status": "success",
        "incident_count": len(
            incidents
        ),
        "orchestration_results": (
            immediate_results
        ),
        "allocation_plan": final_plan,
    }