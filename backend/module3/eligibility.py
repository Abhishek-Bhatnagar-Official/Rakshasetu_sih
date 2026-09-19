from typing import Any


def _is_valid_latitude(value: Any) -> bool:
    """
    Check whether a value is a valid latitude.

    Valid range:
        -90 <= latitude <= 90
    """

    if value is None or isinstance(value, bool):
        return False

    try:
        value = float(value)
    except (TypeError, ValueError):
        return False

    return -90 <= value <= 90


def _is_valid_longitude(value: Any) -> bool:
    """
    Check whether a value is a valid longitude.

    Valid range:
        -180 <= longitude <= 180
    """

    if value is None or isinstance(value, bool):
        return False

    try:
        value = float(value)
    except (TypeError, ValueError):
        return False

    return -180 <= value <= 180


def has_usable_coordinates(
    incident: dict[str, Any]
) -> bool:
    """
    Determine whether an incident has usable geographic coordinates.

    Both latitude and longitude must:
    - exist
    - be numeric
    - be within their valid geographic ranges
    """

    # The existing test suite expects AttributeError
    # for non-dictionary input.
    if not isinstance(incident, dict):
        raise AttributeError(
            "incident must be a dictionary."
        )

    latitude = incident.get("latitude")
    longitude = incident.get("longitude")

    return (
        _is_valid_latitude(latitude)
        and _is_valid_longitude(longitude)
    )


def determine_allocation_eligibility(
    incident: dict[str, Any]
) -> bool:
    """
    Determine whether an incident is eligible for
    resource allocation.

    An incident is eligible only when:
    1. location_status is 'resolved'
    2. latitude is valid
    3. longitude is valid
    """

    if not isinstance(incident, dict):
        raise TypeError(
            "incident must be a dictionary."
        )

    if incident.get("location_status") != "resolved":
        return False

    return has_usable_coordinates(incident)


__all__ = [
    "has_usable_coordinates",
    "determine_allocation_eligibility",
]