from backend.module4_engine.data import MOCK_RESOURCES
from backend.module4_engine.engine import process_module_4
from backend.optimizer.optimizer import optimize_allocation


def main() -> None:
    print("Creating two competing critical incidents...")

    incidents = [
        {
            "incident_id": "I001",
            "priority_level": "critical",
            "priority_score": 98,
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
            "priority_level": "critical",
            "priority_score": 90,
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
    # Resource setup
    # --------------------------------------------------------
    #
    # RT01 is the ONLY resource capable of flood_rescue.
    #
    # RT02 is available but lacks the required capability.
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

    rescue_assignments = [
        assignment
        for assignment in plan["assignments"]
        if assignment["resource_id"] == "RT01"
    ]

    # RT01 must not be assigned to both incidents.
    assert len(rescue_assignments) == 1, (
        "RT01 must be assigned to exactly one incident."
    )

    assigned_incident_ids = {
        assignment["incident_id"]
        for assignment in rescue_assignments
    }

    unserved_incident_ids = {
        requirement["incident_id"]
        for requirement in plan["unserved_requirements"]
        if requirement["resource_type"] == "rescue_team"
    }

    # One critical incident must receive the resource.
    assert len(assigned_incident_ids) == 1, (
        "Exactly one critical incident should receive RT01."
    )

    # The other critical incident must remain unserved.
    assert len(unserved_incident_ids) == 1, (
        "Exactly one critical incident should have "
        "an unserved rescue_team requirement."
    )

    # Together, the two sets must contain both incidents.
    assert (
        assigned_incident_ids | unserved_incident_ids
    ) == {"I001", "I002"}, (
        "Both critical incidents must be accounted for "
        "in the allocation result."
    )

    # They must not overlap.
    assert not (
        assigned_incident_ids & unserved_incident_ids
    ), (
        "The same incident cannot simultaneously be "
        "served and unserved."
    )

    print("\nSUCCESS:")
    print("Two critical incidents competed for one resource.")
    print("Only one incident received RT01.")
    print("The other critical incident was marked unserved.")
    print("Resource exclusivity is working correctly.")


if __name__ == "__main__":
    main()