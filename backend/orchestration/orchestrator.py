from datetime import datetime, timezone
from threading import Timer, Lock
from typing import Any

from .models import OrchestrationResult, OptimizationInput
from backend.module4_engine.engine import process_module_4
from backend.module4_engine.data import (
    get_resources,
    mark_resources_assigned,
)
from backend.optimizer.optimizer import optimize_allocation


CONCURRENCY_WINDOW_SECONDS = 120


class Orchestrator:
    """
    Coordinates prioritized incidents before they are sent
    to the optimization pipeline.

    Responsibilities:
    - Receive prioritized incidents from Module 3
    - Immediately release Critical incidents
    - Hold non-critical incidents during the concurrency window
    - Automatically release the batch after 120 seconds
    - Group qualifying incidents into a batch
    - Pass released incidents and the resource inventory
      through Module 4
    - Send the resulting inputs to the allocation optimizer
    - Commit successfully allocated resources as assigned
    - Produce the optimizer-ready input and allocation plan
    """

    def __init__(
        self,
        resources: list[dict[str, Any]],
    ) -> None:
        """
        Initialize the orchestrator.

        Parameters
        ----------
        resources:
            Current resource inventory supplied by Module 4
            / resource inventory manager.
        """

        if not isinstance(resources, list):
            raise TypeError(
                "resources must be a list."
            )

        self._resources = resources

        self._pending_incidents: list[
            dict[str, Any]
        ] = []

        self._window_started_at: datetime | None = None

        self._batch_counter: int = 0

        self._window_timer: Timer | None = None

        self._last_result: OrchestrationResult | None = None

        self._last_allocation_plan: dict[
            str, Any
        ] | None = None

        self._lock = Lock()

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def submit_incident(
        self,
        incident: dict[str, Any],
    ) -> OrchestrationResult | None:
        """
        Submit one prioritized incident.

        Critical incidents bypass the concurrency window
        and are immediately released.

        Non-critical incidents are held until the 120-second
        window expires or the batch is manually flushed.
        """

        self._validate_incident(
            incident
        )

        # ----------------------------------------------------
        # Critical-priority bypass
        # ----------------------------------------------------

        if (
            str(
                incident.get(
                    "priority_level",
                    "",
                )
            ).strip().lower()
            == "critical"
        ):
            return self._release_immediately(
                incident
            )

        # ----------------------------------------------------
        # Pending incident handling
        # ----------------------------------------------------

        with self._lock:

            if not self._pending_incidents:

                self._window_started_at = (
                    datetime.now(timezone.utc)
                )

                self._last_result = None
                self._last_allocation_plan = None

                self._start_window_timer()

            self._pending_incidents.append(
                incident
            )

        return None

    def flush(
        self,
    ) -> OrchestrationResult | None:
        """
        Manually release the currently pending batch.
        """

        with self._lock:

            if not self._pending_incidents:
                return None

            return self._release_pending_batch_locked()

    def check_timer(
        self,
    ) -> OrchestrationResult | None:
        """
        Check whether the current concurrency window has expired.
        """

        with self._lock:

            if not self._pending_incidents:
                return None

            if self._window_started_at is None:
                return None

            current_time = datetime.now(
                timezone.utc
            )

            elapsed = (
                current_time
                - self._window_started_at
            ).total_seconds()

            if (
                elapsed
                >= CONCURRENCY_WINDOW_SECONDS
            ):
                return (
                    self._release_pending_batch_locked()
                )

            return None

    def get_last_result(
        self,
    ) -> OrchestrationResult | None:
        """
        Return the most recently released orchestration result.
        """

        with self._lock:
            return self._last_result

    def get_last_allocation_plan(
        self,
    ) -> dict[str, Any] | None:
        """
        Return the most recently generated allocation plan.
        """

        with self._lock:
            return self._last_allocation_plan

    # --------------------------------------------------------
    # Inventory commitment
    # --------------------------------------------------------

    def _commit_allocation(
        self,
        allocation_plan: dict[str, Any],
    ) -> list[str]:
        """
        Commit resources selected by the optimizer.

        The optimizer itself is deliberately side-effect free.

        This method is the boundary where a proposed allocation
        becomes an actual resource assignment.

        Returns
        -------
        list[str]
            Resource IDs successfully marked as assigned.
        """

        if not isinstance(
            allocation_plan,
            dict,
        ):
            return []

        assignments = allocation_plan.get(
            "assignments",
            [],
        )

        if not isinstance(
            assignments,
            list,
        ):
            return []

        resource_ids: list[str] = []

        for assignment in assignments:

            if not isinstance(
                assignment,
                dict,
            ):
                continue

            resource_id = assignment.get(
                "resource_id"
            )

            if not isinstance(
                resource_id,
                str,
            ):
                continue

            resource_id = resource_id.strip()

            if (
                resource_id
                and resource_id not in resource_ids
            ):
                resource_ids.append(
                    resource_id
                )

        if not resource_ids:
            return []

        assigned_ids = mark_resources_assigned(
            resource_ids
        )

        # Refresh the orchestrator's local reference from the
        # authoritative runtime inventory.
        #
        # This is important because the next optimization batch
        # must see resources that were just assigned.
        refreshed_resources = get_resources()

        self._resources.clear()
        self._resources.extend(
            refreshed_resources
        )

        return assigned_ids

    # --------------------------------------------------------
    # Timer handling
    # --------------------------------------------------------

    def _start_window_timer(self) -> None:
        """
        Start the real-time 120-second concurrency timer.
        """

        if self._window_timer is not None:
            self._window_timer.cancel()

        self._window_timer = Timer(
            CONCURRENCY_WINDOW_SECONDS,
            self._timer_release,
        )

        self._window_timer.daemon = True

        self._window_timer.start()

    def _timer_release(self) -> None:
        """
        Release the pending batch when the timer expires.
        """

        with self._lock:

            if not self._pending_incidents:
                return

            self._release_pending_batch_locked()

    def _cancel_window_timer(self) -> None:
        """
        Cancel the active concurrency timer.
        """

        if self._window_timer is not None:

            self._window_timer.cancel()

            self._window_timer = None

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    @staticmethod
    def _validate_incident(
        incident: dict[str, Any],
    ) -> None:
        """
        Validate the minimum Module 3 incident contract.
        """

        if not isinstance(
            incident,
            dict,
        ):
            raise TypeError(
                "incident must be a dictionary."
            )

        required_fields = [
            "incident_id",
            "priority_level",
            "reported_at",
        ]

        missing = [
            field
            for field in required_fields
            if field not in incident
        ]

        if missing:
            raise ValueError(
                "Incident missing required fields: "
                f"{missing}"
            )

        # Validate timestamp format at the orchestration
        # boundary, but do not use it for window timing.
        Orchestrator._parse_timestamp(
            incident["reported_at"]
        )

    # --------------------------------------------------------
    # Time handling
    # --------------------------------------------------------

    @staticmethod
    def _parse_timestamp(
        timestamp: str,
    ) -> datetime:
        """
        Convert an ISO-8601 timestamp into a timezone-aware
        datetime.

        This timestamp is validated only for contract correctness.
        It does NOT control the real-time concurrency window.
        """

        if not isinstance(
            timestamp,
            str,
        ):
            raise TypeError(
                "reported_at must be a string."
            )

        try:
            parsed = datetime.fromisoformat(
                timestamp.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError as exc:
            raise ValueError(
                "reported_at must be a valid "
                "ISO-8601 timestamp."
            ) from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    # --------------------------------------------------------
    # Module 4 + Optimizer integration
    # --------------------------------------------------------

    def _prepare_optimization_input(
        self,
        incidents: list[dict[str, Any]],
    ) -> tuple[
        OptimizationInput,
        dict[str, Any],
    ]:
        """
        Pass released incidents through Module 4 and then
        into the allocation optimizer.

        Returns:
            optimizer input,
            allocation plan
        """

        # ----------------------------------------------------
        # Module 4
        # ----------------------------------------------------

        module4_output = process_module_4(
            prioritized_incidents=incidents,
            resources=self._resources,
        )

        optimization_input: OptimizationInput = {
            "incidents": incidents,
            "resources": module4_output[
                "resources"
            ],
            "travel_costs": module4_output[
                "travel_costs"
            ],
        }

        # ----------------------------------------------------
        # Optimizer
        # ----------------------------------------------------

        allocation_plan = optimize_allocation(
            prioritized_incidents=incidents,
            allocation_inputs={
                "resources": module4_output[
                    "resources"
                ],
                "travel_costs": module4_output[
                    "travel_costs"
                ],
            },
        )

        # ----------------------------------------------------
        # Commit selected resources
        # ----------------------------------------------------
        #
        # The optimizer proposes.
        # The orchestrator commits.
        #

        assigned_resource_ids = (
            self._commit_allocation(
                allocation_plan
            )
        )

        # Keep useful metadata in the plan without changing
        # the optimizer's core contract.
        allocation_plan[
            "assigned_resource_ids"
        ] = assigned_resource_ids

        return (
            optimization_input,
            allocation_plan,
        )

    # --------------------------------------------------------
    # Release handling
    # --------------------------------------------------------

    def _release_immediately(
        self,
        incident: dict[str, Any],
    ) -> OrchestrationResult:
        """
        Immediately release a Critical incident.

        Critical incidents do not wait for the
        two-minute concurrency window.
        """

        with self._lock:

            self._batch_counter += 1

            batch_id = (
                f"B{self._batch_counter:03d}"
            )

            (
                optimization_input,
                allocation_plan,
            ) = self._prepare_optimization_input(
                [incident]
            )

            self._last_allocation_plan = (
                allocation_plan
            )

            result: OrchestrationResult = {
                "batch_id": batch_id,
                "incident_ids": [
                    incident["incident_id"]
                ],
                "batch_type": "single",
                "release_reason": (
                    "critical_priority"
                ),
                "optimization_input": (
                    optimization_input
                ),
            }

            self._last_result = result

            return result

    def _release_pending_batch_locked(
        self,
    ) -> OrchestrationResult:
        """
        Release all incidents currently inside the
        concurrency window as one optimization batch.

        IMPORTANT:
            self._lock must already be held.
        """

        self._batch_counter += 1

        batch_id = (
            f"B{self._batch_counter:03d}"
        )

        incidents = list(
            self._pending_incidents
        )

        batch_type = (
            "single"
            if len(incidents) == 1
            else "concurrent"
        )

        (
            optimization_input,
            allocation_plan,
        ) = self._prepare_optimization_input(
            incidents
        )

        self._last_allocation_plan = (
            allocation_plan
        )

        result: OrchestrationResult = {
            "batch_id": batch_id,
            "incident_ids": [
                incident["incident_id"]
                for incident in incidents
            ],
            "batch_type": batch_type,
            "release_reason": "window_expired",
            "optimization_input": (
                optimization_input
            ),
        }

        self._last_result = result

        # Clear pending batch.
        self._pending_incidents.clear()

        self._window_started_at = None

        self._cancel_window_timer()

        return result