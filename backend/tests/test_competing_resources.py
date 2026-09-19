from backend.module4_engine.data import MOCK_RESOURCES
from backend.module4_engine.engine import process_module_4
from backend.optimizer.optimizer import optimize_allocation


def main() -> None:
    print("Creating competing incidents...")

    incidents = [
        {
            "incident_id": "I001",
            "priority_level": "critical",
            "priority_score": 95,
            "reported_at": "2026-09-08T10:00:00+00:00",
            "latitude": 27.4728,
            "longitude": 94.9120,
            "allocation_eligible": True,
            "resource_requirements": [
                {
                    "resource_type": "rescue_team",
                    "minimum_count": 1,
                    "required_capabilities": ["flood_rescue"],
                }
            ],
        },
        {
            "incident_id": "I002",
            "priority_level": "high",
            "priority_score": 80,
            "reported_at": "2026-09-08T10:01:00+00:00",
            "latitude": 26.1445,
            "longitude": 91.7362,
            "allocation_eligible": True,
            "resource_requirements": [
                {
                    "resource_type": "rescue_team",
                    "minimum_count": 1,
                    "required_capabilities": ["flood_rescue"],
                }
            ],
        },
    ]

    # --------------------------------------------------------
    # Make the resource competition explicit
    # --------------------------------------------------------
    #
    # RT01 is the only available resource capable of
    # flood_rescue.
    #
    # RT02 does not have flood_rescue capability.
    #
    resources = [
        resource
        for resource in MOCK_RESOURCES
        if resource["resource_id"] in {"RT01", "RT02"}
    ]

    print("Resources available for test:")
    for resource in resources:
        print(
            f"  {resource['resource_id']}: "
            f"{resource['resource_type']} - "
            f"{resource['capabilities']} - "
            f"{resource['status']}"
        )

    # --------------------------------------------------------
    # Prepare Module 4 output
    # --------------------------------------------------------

    print("\nRunning Module 4...")

    module4_output = process_module_4(
        prioritized_incidents=incidents,
        resources=resources,
    )

    allocation_inputs = {
        "resources": module4_output["resources"],
        "travel_costs": module4_output["travel_costs"],
    }

    print(
        f"Travel cost entries generated: "
        f"{len(module4_output['travel_costs'])}"
    )

    # --------------------------------------------------------
    # Run optimizer
    # --------------------------------------------------------

    print("\nRunning allocation optimizer...")

    plan = optimize_allocation(
        prioritized_incidents=incidents,
        allocation_inputs=allocation_inputs,
    )

    print("\nALLOCATION PLAN")
    print("----------------")
    print(f"Plan ID: {plan['plan_id']}")
    print(f"Status: {plan['status']}")

    print("\nAssignments:")
    for assignment in plan["assignments"]:
        print(
            f"  Incident {assignment['incident_id']} "
            f"-> Resource {assignment['resource_id']} "
            f"({assignment['resource_type']})"
        )

    print("\nUnserved requirements:")
    for unserved in plan["unserved_requirements"]:
        print(
            f"  Incident {unserved['incident_id']} "
            f"-> {unserved['resource_type']} "
            f"x{unserved['required_count']} "
            f"| {unserved['reason']}"
        )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    assigned_incidents = {
        assignment["incident_id"]
        for assignment in plan["assignments"]
    }

    unserved_incidents = {
        requirement["incident_id"]
        for requirement in plan["unserved_requirements"]
    }

    # Exactly one incident should receive RT01.
    rescue_assignments = [
        assignment
        for assignment in plan["assignments"]
        if assignment["resource_id"] == "RT01"
    ]

    assert len(rescue_assignments) == 1, (
        "RT01 must be assigned to exactly one incident."
    )

    # Both incidents cannot receive the same resource.
    assert len(assigned_incidents) <= 2

    # Because only one suitable rescue team exists,
    # at least one incident must remain unserved.
    assert len(unserved_incidents) == 1, (
        "Exactly one incident should have an unserved "
        "rescue_team requirement."
    )

    # The same incident must not both receive and lack
    # the same required resource in this test.
    assert not (
        assigned_incidents & unserved_incidents
    ), (
        "An incident should not simultaneously appear "
        "as assigned and unserved for this test."
    )

    # The higher-priority incident should win the competition.
    assert "I001" in assigned_incidents, (
        "Critical incident I001 should receive the "
        "limited rescue team."
    )

    assert "I002" in unserved_incidents, (
        "Lower-priority incident I002 should remain "
        "unserved because RT01 is already allocated."
    )

    print("\nSUCCESS:")
    print("Resource competition was handled correctly.")
    print("RT01 was allocated to the higher-priority incident.")
    print("The lower-priority incident was marked unserved.")


if __name__ == "__main__":
    main()