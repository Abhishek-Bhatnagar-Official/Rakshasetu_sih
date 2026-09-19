from typing import Any, TypedDict


class Assignment(TypedDict):
    incident_id: str
    resource_id: str
    resource_type: str
    distance_km: float
    travel_time_min: int | None
    reasons: list[str]


class UnservedRequirement(TypedDict):
    incident_id: str
    resource_type: str
    required_count: int
    reason: str


class AllocationPlan(TypedDict):
    plan_id: str
    status: str
    generated_at: str
    assignments: list[Assignment]
    unserved_requirements: list[UnservedRequirement]


class AllocationInputs(TypedDict):
    resources: list[dict[str, Any]]
    travel_costs: list[dict[str, Any]]