from backend.module4_engine.data import MOCK_RESOURCES
from backend.module4_engine.engine import process_module_4
from backend.optimizer.optimizer import optimize_allocation


def main() -> None:
    print("Creating four incidents with mixed resource requirements...")
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
                    "required_capabilities": ["first_aid"],
                },
                {
                    "resource_type": "ambulance",
                    "minimum_count": 1,
                    "required_capabilities": ["medical_transport"],
                },
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
                    "required_capabilities": ["first_aid"],
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
                    "required_capabilities": ["first_aid"],
                },
                {
                    "resource_type": "boat",
                    "minimum_count": 1,
                    "required_capabilities": ["water_rescue"],
                },
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
                    "required_capabilities": ["first_aid"],
                }
            ],
        },
    ]

    # --------------------------------------------------------
    # Resource setup
    # --------------------------------------------------------
    #
    # RT01 and RT02 can both satisfy the rescue_team
    # requirement because both have first_aid capability.
    #
    # This creates genuine resource competition between
    # I001, I002, I003 and I004.
    #
    # AMB01 is available for I001's medical requirement.
    # BOAT01 is available for I003's water-rescue requirement.
    #

    resources = [
        resource
        for resource in MOCK_RESOURCES
        if resource["resource_id"] in {
            "RT01",
            "RT02",
            "AMB01",
            "BOAT01",
        }
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
        incident = next(
            incident
            for incident in incidents
            if incident["incident_id"] == assignment["incident_id"]
        )

        priority = incident["priority_level"]

        print(
            f"  Incident {assignment['incident_id']} "
            f"({priority}) -> "
            f"Resource {assignment['resource_id']} "
            f"({assignment['resource_type']})"
        )

    print("\nUnserved requirements:")

    for unserved in plan["unserved_requirements"]:
        incident = next(
            incident
            for incident in incidents
            if incident["incident_id"] == unserved["incident_id"]
        )

        priority = incident["priority_level"]

        print(
            f"  Incident {unserved['incident_id']} "
            f"({priority}) -> "
            f"{unserved['resource_type']} "
            f"x{unserved['required_count']} "
            f"| {unserved['reason']}"
        )

    # --------------------------------------------------------
    # Extract rescue-team assignments
    # --------------------------------------------------------

    rescue_assignments = [
        assignment
        for assignment in plan["assignments"]
        if assignment["resource_type"] == "rescue_team"
    ]

    # There are exactly two suitable rescue teams.
    assert len(rescue_assignments) == 2, (
        "Exactly two rescue-team assignments should be made."
    )

    assigned_rescue_incidents = {
        assignment["incident_id"]
        for assignment in rescue_assignments
    }

    assigned_rescue_resources = {
        assignment["resource_id"]
        for assignment in rescue_assignments
    }

    # Both high-priority incidents should receive the
    # competing rescue-team resources.
    assert assigned_rescue_incidents == {"I001", "I002"}, (
        "Both high-priority incidents should receive the "
        "two available suitable rescue teams."
    )

    # RT01 and RT02 must each be used exactly once.
    assert assigned_rescue_resources == {"RT01", "RT02"}, (
        "Both suitable rescue teams should be allocated."
    )

    # --------------------------------------------------------
    # Verify I001 receives its ambulance.
    # --------------------------------------------------------

    ambulance_assignments = [
        assignment
        for assignment in plan["assignments"]
        if assignment["resource_type"] == "ambulance"
    ]

    assert len(ambulance_assignments) == 1, (
        "I001 should receive the available ambulance."
    )

    assert ambulance_assignments[0]["incident_id"] == "I001", (
        "The ambulance should be allocated to I001."
    )

    # --------------------------------------------------------
    # Verify I003 receives its boat.
    # --------------------------------------------------------

    boat_assignments = [
        assignment
        for assignment in plan["assignments"]
        if assignment["resource_type"] == "boat"
    ]

    assert len(boat_assignments) == 1, (
        "I003 should receive the available boat."
    )

    assert boat_assignments[0]["incident_id"] == "I003", (
        "The boat should be allocated to I003."
    )

    # --------------------------------------------------------
    # Verify lower-priority rescue requirements are unserved.
    # --------------------------------------------------------

    unserved_rescue_incidents = {
        requirement["incident_id"]
        for requirement in plan["unserved_requirements"]
        if requirement["resource_type"] == "rescue_team"
    }

    assert unserved_rescue_incidents == {"I003", "I004"}, (
        "I003 and I004 should remain unserved for rescue_team "
        "because both rescue teams were allocated to the "
        "higher-priority incidents."
    )

    # --------------------------------------------------------
    # Verify no resource was double-allocated.
    # --------------------------------------------------------

    assigned_resource_ids = [
        assignment["resource_id"]
        for assignment in plan["assignments"]
    ]

    assert len(assigned_resource_ids) == len(
        set(assigned_resource_ids)
    ), (
        "A resource must not be assigned to multiple "
        "requirements."
    )

    # --------------------------------------------------------
    # Final success message
    # --------------------------------------------------------

    print("\nSUCCESS:")
    print("Mixed resource competition was handled correctly.")
    print("Both high-priority incidents received rescue teams.")
    print("I001 received the available ambulance.")
    print("I003 received the available boat.")
    print("I003 and I004 remained unserved for rescue_team.")
    print("No resource was double-allocated.")


if __name__ == "__main__":
    main()