from typing import Any, Literal, TypedDict
from backend.optimizer.models import AllocationPlan

# ============================================================
# Orchestration Type Definitions
# ============================================================

BatchType = Literal["single", "concurrent"]

BatchStatus = Literal[
    "collecting",
    "ready_for_optimization",
    "optimized",
    "completed",
]

ReleaseReason = Literal[
    "critical_priority",
    "window_expired",
]


# ============================================================
# Optimization Input
# ============================================================

class OptimizationInput(TypedDict):
    """
    Input prepared by the orchestration layer for the
    optimization engine.

    This combines:
    - prioritized incidents from Module 3
    - resource/travel information from Module 4
    """

    incidents: list[dict[str, Any]]
    resources: list[dict[str, Any]]
    travel_costs: list[dict[str, Any]]


# ============================================================
# Orchestration Batch
# ============================================================

class OrchestrationBatch(TypedDict):
    """
    Represents a group of incidents that will be processed
    together by the optimization engine.
    """

    batch_id: str

    incident_ids: list[str]

    incidents: list[dict[str, Any]]

    batch_type: BatchType

    status: BatchStatus

    release_reason: ReleaseReason

    window_started_at: str

    optimization_input: OptimizationInput | None


# ============================================================
# Orchestration Result
# ============================================================

class OrchestrationResult(TypedDict):
    """
    Result returned when the orchestration layer releases
    an incident or batch for optimization.
    """

    batch_id: str

    incident_ids: list[str]

    batch_type: BatchType

    release_reason: ReleaseReason

    optimization_input: OptimizationInput

    allocation_plan: AllocationPlan