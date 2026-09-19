from backend.module4_engine.data import MOCK_RESOURCES
from backend.module4_engine.engine import process_module_4
from backend.optimizer.optimizer import optimize_allocation


def main() -> None:
    print("Creating four competing incidents...")
    print("2 HIGH + 1 MEDIUM + 1 LOW")

    incidents = [
        {
            "incident_id": "I001",
            "priority_level": "high",
            "priority_score": 85,
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
        {
            "incident_id": "I003",
            "priority_level": "medium",
            "priority_score": 60,
            "reported_at": "2026-09-08T10:02:00+00:00",
            "latitude": 25.5788,
            "longitude": 91.8933,
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
            "incident_id": "I004",
            "priority_level": "low",
            "priority_score": 30,
            "reported_at": "2026-09-08T10:03:00+00:00",
            "latitude": 26.2000,
            "longitude": 91.7000,
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
    # Resource setup
    # --------------------------------------------------------
    #
    # RT01 is the ONLY available resource capable of
    # flood_rescue.
    #
    # RT02 is intentionally included but cannot satisfy
    # the requirement because it only has first_aid.
    #

    resources = [
        resource
        for resource in MOCK_RESOURCES
        if resource["resource_id"] in {"RT01", "RT02"}
    ]

    print("\nResources available for test:")

    for resource in resources:
        print(
            f"  {resource['resource_id']}: "
            f"{resource['resource_type']} - "
            f"{resource['capabilities']} - "
            f"{resource['status']}"
        )

    # --------------------------------------------------------
    # Module 4
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
        "Travel cost entries generated:",
        len(module4_output["travel_costs"]),
    )

    # --------------------------------------------------------
    # Optimizer
    # --------------------------------------------------------

    print("\nRunning allocation optimizer...")

    plan = optimize_allocation(
        prioritized_incidents=incidents,
        allocation_inputs=allocation_inputs,
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print("\nALLOCATION PLAN")
    print("----------------")
    print(f"Plan ID: {plan['plan_id']}")
    print(f"Status: {plan['status']}")

    print("\nAssignments:")

    for assignment in plan["assignments"]:
        assignment_incident = next(
            incident
            for incident in incidents
            if incident["incident_id"] == assignment["incident_id"]
        )

        priority = assignment_incident["priority_level"]

        print(
            f"  Incident {assignment['incident_id']} "
            f"({priority}) -> "
            f"Resource {assignment['resource_id']} "
            f"({assignment['resource_type']})"
        )

    print("\nUnserved requirements:")

    for unserved in plan["unserved_requirements"]:
        priority_incident = next(
            incident
            for incident in incidents
            if incident["incident_id"] == unserved["incident_id"]
        )

        priority = priority_incident["priority_level"]

        print(
            f"  Incident {unserved['incident_id']} "
            f"({priority}) -> "
            f"{unserved['resource_type']} "
            f"x{unserved['required_count']} "
            f"| {unserved['reason']}"
        )

    # --------------------------------------------------------
    # Assertions
    # --------------------------------------------------------

    rescue_assignments = [
        assignment
        for assignment in plan["assignments"]
        if assignment["resource_type"] == "rescue_team"
    ]

    # Only one suitable rescue team exists.
    assert len(rescue_assignments) == 1, (
        "Exactly one incident should receive the "
        "available rescue team."
    )

    assigned_incident_id = rescue_assignments[0]["incident_id"]

    # The winner must be one of the two HIGH-priority
    # incidents.
    assert assigned_incident_id in {"I001", "I002"}, (
        "A high-priority incident should win over "
        "medium and low-priority incidents."
    )

    # --------------------------------------------------------
    # Verify all remaining incidents are unserved.
    # --------------------------------------------------------

    unserved_incident_ids = {
        requirement["incident_id"]
        for requirement in plan["unserved_requirements"]
        if requirement["resource_type"] == "rescue_team"
    }

    expected_unserved = {
        "I001",
        "I002",
        "I003",
        "I004",
    } - {assigned_incident_id}

    assert unserved_incident_ids == expected_unserved, (
        "Every incident other than the winning high-priority "
        "incident should be marked unserved."
    )

    # --------------------------------------------------------
    # Verify no resource was double-allocated.
    # --------------------------------------------------------

    assigned_resource_ids = [
        assignment["resource_id"]
        for assignment in rescue_assignments
    ]

    assert len(assigned_resource_ids) == len(
        set(assigned_resource_ids)
    ), (
        "A resource must not be assigned to multiple "
        "incidents."
    )

    print("\nSUCCESS:")
    print("Priority competition was handled correctly.")
    print(
        f"{assigned_incident_id} received the limited "
        "rescue_team resource."
    )
    print("The other high-priority incident remained unserved.")
    print("The medium-priority incident remained unserved.")
    print("The low-priority incident remained unserved.")
    print("No resource was double-allocated.")


if __name__ == "__main__":
    main()