from datetime import datetime, timezone
from typing import Any

from ortools.sat.python import cp_model

from .models import (
    AllocationInputs,
    AllocationPlan,
    Assignment,
    UnservedRequirement,
)


# ---------------------------------------------------------------------
# Objective weights
# ---------------------------------------------------------------------

PRIORITY_UNSERVED_PENALTY = {
    "critical": 100_000,
    "high": 50_000,
    "medium": 20_000,
    "low": 5_000,
}


DISTANCE_COST_MULTIPLIER = 100


class AllocationOptimizer:
    """
    Global multi-incident resource allocation optimizer.

    The optimizer receives:
        - prioritized incidents
        - Module 4 resource inventory
        - Module 4 travel costs

    It produces:
        allocation_plan

    The optimizer does NOT:
        - create incidents
        - calculate priority
        - calculate resource requirements
        - calculate routes
        - mutate the resource inventory
        - dispatch resources
        - approve/reject plans
    """

    def __init__(self) -> None:
        self._plan_counter = 0

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def optimize(
        self,
        prioritized_incidents: list[dict[str, Any]],
        allocation_inputs: AllocationInputs,
    ) -> AllocationPlan:
        """
        Compute a global resource allocation plan.

        All incidents in the supplied batch are optimized
        together.

        A resource can be assigned to at most one requirement
        across the entire batch.

        IMPORTANT:
            This function is side-effect free. It only produces
            an allocation plan. Actual resource status mutation
            happens after the plan is accepted/committed by the
            orchestration layer.
        """

        self._validate_inputs(
            prioritized_incidents,
            allocation_inputs,
        )

        self._plan_counter += 1
        plan_id = f"P{self._plan_counter:03d}"

        resources = allocation_inputs["resources"]
        travel_costs = allocation_inputs["travel_costs"]

        # ----------------------------------------------------
        # Build lookup tables
        # ----------------------------------------------------

        resource_by_id = {
            resource["resource_id"]: resource
            for resource in resources
            if resource.get("resource_id")
        }

        incident_by_id = {
            incident["incident_id"]: incident
            for incident in prioritized_incidents
            if incident.get("incident_id")
        }

        travel_by_pair = {
            (
                travel["resource_id"],
                travel["incident_id"],
            ): travel
            for travel in travel_costs
            if (
                travel.get("resource_id")
                and travel.get("incident_id")
            )
        }

        # ----------------------------------------------------
        # Build optimization model
        # ----------------------------------------------------

        model = cp_model.CpModel()

        assignment_vars: dict[
            tuple[str, int, str],
            Any,
        ] = {}

        unmet_vars: dict[
            tuple[str, int],
            Any,
        ] = {}

        objective_terms: list[Any] = []

        # ----------------------------------------------------
        # Create variables for every valid candidate
        # ----------------------------------------------------

        for incident in prioritized_incidents:

            if not incident.get(
                "allocation_eligible",
                False,
            ):
                continue

            incident_id = incident.get("incident_id")

            if not incident_id:
                continue

            priority_level = str(
                incident.get(
                    "priority_level",
                    "low",
                )
            ).strip().lower()

            unmet_penalty = PRIORITY_UNSERVED_PENALTY.get(
                priority_level,
                PRIORITY_UNSERVED_PENALTY["low"],
            )

            requirements = incident.get(
                "resource_requirements",
                [],
            )

            if not isinstance(requirements, list):
                continue

            for req_index, requirement in enumerate(
                requirements
            ):

                if not isinstance(requirement, dict):
                    continue

                resource_type = requirement.get(
                    "resource_type"
                )

                if not resource_type:
                    continue

                required_capabilities = set(
                    requirement.get(
                        "required_capabilities",
                        [],
                    )
                    if isinstance(
                        requirement.get(
                            "required_capabilities",
                            [],
                        ),
                        list,
                    )
                    else []
                )

                minimum_count = self._safe_positive_int(
                    requirement.get(
                        "minimum_count",
                        0,
                    )
                )

                if minimum_count <= 0:
                    continue

                # ------------------------------------------------
                # Unserved requirement variable
                # ------------------------------------------------

                unmet = model.NewIntVar(
                    0,
                    minimum_count,
                    (
                        f"unmet_"
                        f"{incident_id}_"
                        f"{req_index}"
                    ),
                )

                unmet_vars[
                    (incident_id, req_index)
                ] = unmet

                # Higher priority incidents receive much stronger
                # penalties for remaining unserved.
                objective_terms.append(
                    unmet * unmet_penalty
                )

                # ------------------------------------------------
                # Candidate resource variables
                # ------------------------------------------------

                candidate_vars = []

                for resource in resources:

                    resource_id = resource.get(
                        "resource_id"
                    )

                    if not resource_id:
                        continue

                    # Only currently available resources can be
                    # considered.
                    if resource.get("status") != "available":
                        continue

                    # Resource type must match.
                    if (
                        resource.get("resource_type")
                        != resource_type
                    ):
                        continue

                    # Resource must have every required capability.
                    resource_capabilities = set(
                        resource.get(
                            "capabilities",
                            [],
                        )
                        if isinstance(
                            resource.get(
                                "capabilities",
                                [],
                            ),
                            list,
                        )
                        else []
                    )

                    if not required_capabilities.issubset(
                        resource_capabilities
                    ):
                        continue

                    # Travel information must exist.
                    travel = travel_by_pair.get(
                        (
                            resource_id,
                            incident_id,
                        )
                    )

                    if travel is None:
                        continue

                    # Route must be available.
                    if not travel.get(
                        "route_available",
                        False,
                    ):
                        continue

                    # Distance must be usable.
                    distance_km = self._safe_non_negative_float(
                        travel.get("distance_km")
                    )

                    if distance_km is None:
                        continue

                    variable = model.NewBoolVar(
                        (
                            f"assign_"
                            f"{incident_id}_"
                            f"{req_index}_"
                            f"{resource_id}"
                        )
                    )

                    assignment_vars[
                        (
                            incident_id,
                            req_index,
                            resource_id,
                        )
                    ] = variable

                    candidate_vars.append(variable)

                    distance_cost = int(
                        round(
                            distance_km
                            * DISTANCE_COST_MULTIPLIER
                        )
                    )

                    objective_terms.append(
                        variable * distance_cost
                    )

                # ------------------------------------------------
                # Requirement fulfillment constraint
                # ------------------------------------------------
                #
                # assigned resources + unmet units
                # must equal required quantity.
                #
                # Example:
                #
                # required = 3
                # assigned = 2
                # unmet = 1
                #
                # 2 + 1 = 3
                #
                model.Add(
                    sum(candidate_vars) + unmet
                    == minimum_count
                )

        # ----------------------------------------------------
        # Resource exclusivity constraint
        # ----------------------------------------------------

        for resource in resources:

            resource_id = resource.get(
                "resource_id"
            )

            if not resource_id:
                continue

            resource_assignment_vars = [
                variable
                for (
                    incident_id,
                    req_index,
                    candidate_resource_id,
                ), variable in assignment_vars.items()
                if candidate_resource_id == resource_id
            ]

            if resource_assignment_vars:
                model.Add(
                    sum(resource_assignment_vars) <= 1
                )

        # ----------------------------------------------------
        # Objective
        # ----------------------------------------------------

        if objective_terms:
            model.Minimize(
                sum(objective_terms)
            )

        # ----------------------------------------------------
        # Solve
        # ----------------------------------------------------

        solver = cp_model.CpSolver()

        # Deterministic enough for prototype demonstrations.
        solver.parameters.num_search_workers = 1

        status = solver.Solve(model)

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            return self._empty_plan(
                plan_id,
                prioritized_incidents,
            )

        # ----------------------------------------------------
        # Extract solution
        # ----------------------------------------------------

        assignments: list[Assignment] = []

        unserved_requirements: list[
            UnservedRequirement
        ] = []

        # ----------------------------------------------------
        # Assigned resources
        # ----------------------------------------------------

        for (
            incident_id,
            req_index,
            resource_id,
        ), variable in assignment_vars.items():

            if solver.Value(variable) != 1:
                continue

            resource = resource_by_id.get(
                resource_id
            )

            travel = travel_by_pair.get(
                (
                    resource_id,
                    incident_id,
                )
            )

            incident = incident_by_id.get(
                incident_id
            )

            if (
                resource is None
                or travel is None
                or incident is None
            ):
                continue

            assignment: Assignment = {
                "incident_id": incident_id,
                "resource_id": resource_id,
                "resource_type": resource[
                    "resource_type"
                ],
                "distance_km": float(
                    travel["distance_km"]
                ),
                "travel_time_min": travel.get(
                    "travel_time_min"
                ),
                "reasons": self._build_assignment_reasons(
                    incident,
                    resource,
                    travel,
                ),
            }

            assignments.append(
                assignment
            )

        # ----------------------------------------------------
        # Unserved requirements
        # ----------------------------------------------------

        for (
            incident_id,
            req_index,
        ), unmet_variable in unmet_vars.items():

            unmet_count = solver.Value(
                unmet_variable
            )

            if unmet_count <= 0:
                continue

            incident = incident_by_id.get(
                incident_id
            )

            if incident is None:
                continue

            requirements = incident.get(
                "resource_requirements",
                [],
            )

            if (
                not isinstance(requirements, list)
                or req_index >= len(requirements)
            ):
                continue

            requirement = requirements[
                req_index
            ]

            reason = self._build_unserved_reason(
                incident,
                requirement,
            )

            unserved: UnservedRequirement = {
                "incident_id": incident_id,
                "resource_type": requirement[
                    "resource_type"
                ],
                "required_count": unmet_count,
                "reason": reason,
            }

            unserved_requirements.append(
                unserved
            )

        # ----------------------------------------------------
        # Return allocation plan
        # ----------------------------------------------------

        return {
            "plan_id": plan_id,
            "status": "proposed",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "assignments": assignments,
            "unserved_requirements": (
                unserved_requirements
            ),
        }

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        prioritized_incidents: list[dict[str, Any]],
        allocation_inputs: AllocationInputs,
    ) -> None:
        """
        Validate the optimizer's basic input contract.
        """

        if not isinstance(
            prioritized_incidents,
            list,
        ):
            raise TypeError(
                "prioritized_incidents must be a list."
            )

        if not isinstance(
            allocation_inputs,
            dict,
        ):
            raise TypeError(
                "allocation_inputs must be a dictionary."
            )

        if "resources" not in allocation_inputs:
            raise ValueError(
                "allocation_inputs must contain resources."
            )

        if "travel_costs" not in allocation_inputs:
            raise ValueError(
                "allocation_inputs must contain travel_costs."
            )

        if not isinstance(
            allocation_inputs["resources"],
            list,
        ):
            raise TypeError(
                "allocation_inputs['resources'] "
                "must be a list."
            )

        if not isinstance(
            allocation_inputs["travel_costs"],
            list,
        ):
            raise TypeError(
                "allocation_inputs['travel_costs'] "
                "must be a list."
            )

        # Validate incident IDs because they are used as CP-SAT
        # variable-name components and lookup keys.
        for incident in prioritized_incidents:

            if not isinstance(
                incident,
                dict,
            ):
                raise TypeError(
                    "Each prioritized incident "
                    "must be a dictionary."
                )

            if not incident.get("incident_id"):
                raise ValueError(
                    "Each incident must contain "
                    "incident_id."
                )

        # Validate resource IDs.
        for resource in allocation_inputs["resources"]:

            if not isinstance(
                resource,
                dict,
            ):
                raise TypeError(
                    "Each resource must be a dictionary."
                )

            if not resource.get("resource_id"):
                raise ValueError(
                    "Each resource must contain "
                    "resource_id."
                )

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _safe_positive_int(
        value: Any,
    ) -> int:
        """
        Convert a value into a non-negative integer.

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
                return max(
                    0,
                    int(float(value)),
                )
            except (
                TypeError,
                ValueError,
            ):
                return 0

        return 0

    @staticmethod
    def _safe_non_negative_float(
        value: Any,
    ) -> float | None:
        """
        Safely normalize a distance value.

        Returns None when the value is unusable.
        """

        if value is None:
            return None

        try:
            converted = float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

        if converted != converted:  # NaN
            return None

        if converted < 0:
            return None

        return converted

    @staticmethod
    def _build_assignment_reasons(
        incident: dict[str, Any],
        resource: dict[str, Any],
        travel: dict[str, Any],
    ) -> list[str]:
        """
        Generate human-readable reasons for an assignment.
        """

        reasons = [
            "required capability",
            "resource available",
        ]

        priority_level = str(
            incident.get(
                "priority_level",
                "",
            )
        ).strip().lower()

        if priority_level in {
            "critical",
            "high",
        }:
            reasons.append(
                f"{priority_level} incident priority"
            )

        distance = travel.get(
            "distance_km"
        )

        if distance is not None:
            reasons.append(
                "low suitable allocation cost"
            )

        return reasons

    @staticmethod
    def _build_unserved_reason(
        incident: dict[str, Any],
        requirement: dict[str, Any],
    ) -> str:
        """
        Explain why a requirement could not be fully served.
        """

        if not incident.get(
            "allocation_eligible",
            False,
        ):
            return (
                "incident is not eligible for "
                "geographic allocation"
            )

        return (
            "resource scarcity: insufficient "
            "suitable available resources"
        )

    @staticmethod
    def _empty_plan(
        plan_id: str,
        prioritized_incidents: list[dict[str, Any]],
    ) -> AllocationPlan:
        """
        Return a safe empty plan if the solver cannot
        produce a feasible solution.
        """

        unserved_requirements = []

        for incident in prioritized_incidents:

            if not incident.get(
                "allocation_eligible",
                False,
            ):
                continue

            requirements = incident.get(
                "resource_requirements",
                [],
            )

            if not isinstance(
                requirements,
                list,
            ):
                continue

            for requirement in requirements:

                if not isinstance(
                    requirement,
                    dict,
                ):
                    continue

                count = AllocationOptimizer._safe_positive_int(
                    requirement.get(
                        "minimum_count",
                        0,
                    )
                )

                if count <= 0:
                    continue

                unserved_requirements.append(
                    {
                        "incident_id": incident[
                            "incident_id"
                        ],
                        "resource_type": requirement[
                            "resource_type"
                        ],
                        "required_count": count,
                        "reason": (
                            "optimizer could not "
                            "produce a feasible solution"
                        ),
                    }
                )

        return {
            "plan_id": plan_id,
            "status": "proposed",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "assignments": [],
            "unserved_requirements": (
                unserved_requirements
            ),
        }


# ------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------

_default_optimizer = AllocationOptimizer()


def optimize_allocation(
    prioritized_incidents: list[dict[str, Any]],
    allocation_inputs: AllocationInputs,
) -> AllocationPlan:
    """
    Convenience wrapper around AllocationOptimizer.

    This is the function that the orchestration layer can
    call directly.
    """

    return _default_optimizer.optimize(
        prioritized_incidents,
        allocation_inputs,
    )


__all__ = [
    "AllocationOptimizer",
    "optimize_allocation",
]