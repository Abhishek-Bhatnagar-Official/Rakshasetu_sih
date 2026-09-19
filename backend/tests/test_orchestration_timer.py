
import time

from backend.orchestration.orchestrator import Orchestrator
from backend.module4_engine.data import MOCK_RESOURCES


def main():
    o = Orchestrator(MOCK_RESOURCES)

    incident = {
        "incident_id": "I001",
        "priority_level": "high",
        "priority_score": 73,
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
    }

    print("Submitting incident...")

    result = o.submit_incident(incident)

    print("Immediate result:", result)

    if result is not None:
        print("ERROR: Incident was released immediately.")
        return

    print("Incident is being held in the concurrency window.")
    print("Waiting for 120 seconds...")

    time.sleep(120)

    print("120 seconds have passed.")
    print("Checking whether the background timer released the batch...")

    result = None

    for _ in range(10):
        result = o.get_last_result()

        if result is not None:
            break

        time.sleep(1)

    print("Timer result:", result)

    if result is None:
        print("ERROR: Timer did not release the batch.")
        return

    if result["release_reason"] != "window_expired":
        print(
            "ERROR: Unexpected release reason:",
            result["release_reason"],
        )
        return

    if result["incident_ids"] != ["I001"]:
        print(
            "ERROR: Unexpected incident IDs:",
            result["incident_ids"],
        )
        return

    print("SUCCESS: Incident was automatically released after 120 seconds.")


if __name__ == "__main__":
    main()
