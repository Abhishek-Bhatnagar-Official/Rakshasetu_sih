# engine.py
from geopy.distance import great_circle

def is_resource_eligible(resource: dict, requirement: dict) -> bool:
    """Check if resource is available, matches type, and has required capabilities."""
    if resource.get("status") != "available":
        return False
    if resource.get("resource_type") != requirement.get("resource_type"):
        return False

    req_caps = set(requirement.get("required_capabilities", []))
    res_caps = set(resource.get("capabilities", []))

    return req_caps.issubset(res_caps)


def calculate_travel_cost(resource: dict, incident: dict) -> dict:
    """Calculate geographic distance and travel time with failure handling."""
    try:
        res_coords = (resource["latitude"], resource["longitude"])
        inc_coords = (incident["latitude"], incident["longitude"])

        if None in res_coords or None in inc_coords:
            raise ValueError("Coordinates missing")

        # Straight-line distance calculation via geopy (Haversine baseline)
        dist_km = round(great_circle(res_coords, inc_coords).km, 2)
        travel_time = round((dist_km / 30) * 60)  # Estimated at 30 km/h average speed

        return {
            "resource_id": resource["resource_id"],
            "incident_id": incident["incident_id"],
            "distance_km": dist_km,
            "travel_time_min": travel_time,
            "route_available": True,
        }
    except Exception:
        # Graceful failure handling
        return {
            "resource_id": resource["resource_id"],
            "incident_id": incident["incident_id"],
            "distance_km": None,
            "travel_time_min": None,
            "route_available": False,
        }


def process_module_4(prioritized_incidents: list[dict], resources: list[dict]) -> dict:
    """Main pipeline function returning allocation_inputs for Module 5."""
    travel_costs = []

    for incident in prioritized_incidents:
        if not incident.get("allocation_eligible", False):
            continue

        for resource in resources:
            for req in incident.get("resource_requirements", []):
                if is_resource_eligible(resource, req):
                    cost = calculate_travel_cost(resource, incident)
                    travel_costs.append(cost)

    return {
        "resources": resources,
        "travel_costs": travel_costs
    }