import re
import math
from datetime import datetime
from collections import Counter

from geopy.geocoders import Nominatim

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# -------------------------------------------------------------------
# Geocoder
# -------------------------------------------------------------------

geolocator = Nominatim(
    user_agent="rakshasetu-module2"
)


# -------------------------------------------------------------------
# Allowed incident types
# -------------------------------------------------------------------

ALLOWED_INCIDENT_TYPES = {
    "flood",
    "landslide",
    "road_blockage",
    "building_collapse",
    "storm",
    "other"
}


# -------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------

def safe_text(value):
    """
    Convert a value to a clean string.

    None -> ""
    Other values -> stripped string
    """

    if value is None:
        return ""

    return str(value).strip()


def safe_non_negative_int(value):
    """
    Convert a value to a non-negative integer.

    Returns None when the value is unknown/invalid.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    if number < 0:
        return None

    return number


def safe_nullable_boolean(value):
    """
    Normalize nullable boolean values.

    Accepted:
        True / False
        "true" / "false"
        "yes" / "no"
        "1" / "0"

    Unknown values become None.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        normalized = value.strip().lower()

        if normalized in {
            "true",
            "yes",
            "y",
            "1"
        }:
            return True

        if normalized in {
            "false",
            "no",
            "n",
            "0"
        }:
            return False

    if isinstance(value, (int, float)):

        if value == 1:
            return True

        if value == 0:
            return False

    return None


# -------------------------------------------------------------------
# Geographic similarity
# -------------------------------------------------------------------

def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometres.
    """

    if None in (
        lat1,
        lon1,
        lat2,
        lon2
    ):
        return None

    try:

        lat1 = math.radians(
            float(lat1)
        )

        lon1 = math.radians(
            float(lon1)
        )

        lat2 = math.radians(
            float(lat2)
        )

        lon2 = math.radians(
            float(lon2)
        )

    except (
        TypeError,
        ValueError
    ):
        return None

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    # Numerical safety against tiny floating-point drift.
    a = max(
        0.0,
        min(1.0, a)
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    earth_radius_km = 6371

    return earth_radius_km * c


def geographic_similarity(
    report1,
    report2
):
    """
    Geographic similarity:

    <= 1 km   -> 1.0
    <= 5 km   -> 0.7
    <= 10 km  -> 0.3
    > 10 km   -> 0.0

    Returns None when coordinates are unavailable.
    """

    distance = calculate_distance(
        report1.get("latitude"),
        report1.get("longitude"),
        report2.get("latitude"),
        report2.get("longitude")
    )

    if distance is None:
        return None

    if distance <= 1:
        return 1.0

    if distance <= 5:
        return 0.7

    if distance <= 10:
        return 0.3

    return 0.0


# -------------------------------------------------------------------
# Timestamp processing
# -------------------------------------------------------------------

def parse_timestamp(timestamp):
    """
    Safely parse ISO timestamp.

    Handles:
    - normal ISO timestamps
    - trailing Z
    - invalid timestamps
    """

    if not timestamp:
        return None

    if isinstance(
        timestamp,
        datetime
    ):
        return timestamp

    try:

        value = str(
            timestamp
        ).strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        return datetime.fromisoformat(
            value
        )

    except (
        ValueError,
        TypeError
    ):
        return None


def temporal_similarity(
    report1,
    report2
):
    """
    Temporal similarity:

    <= 30 minutes   -> 1.0
    <= 120 minutes  -> 0.6
    <= 360 minutes  -> 0.2
    > 360 minutes   -> 0.0

    Returns None when timestamps are unavailable.
    """

    time1 = parse_timestamp(
        report1.get("submitted_at")
    )

    time2 = parse_timestamp(
        report2.get("submitted_at")
    )

    if time1 is None or time2 is None:
        return None

    try:

        difference_minutes = abs(
            (
                time1 - time2
            ).total_seconds()
        ) / 60

    except TypeError:
        # Protect against mixing naive and timezone-aware datetimes.
        try:

            time1 = time1.replace(
                tzinfo=None
            )

            time2 = time2.replace(
                tzinfo=None
            )

            difference_minutes = abs(
                (
                    time1 - time2
                ).total_seconds()
            ) / 60

        except Exception:
            return None

    if difference_minutes <= 30:
        return 1.0

    if difference_minutes <= 120:
        return 0.6

    if difference_minutes <= 360:
        return 0.2

    return 0.0


# -------------------------------------------------------------------
# Text similarity
# -------------------------------------------------------------------

def calculate_text_similarities(
    reports
):
    """
    Calculate TF-IDF cosine similarity between report descriptions.

    Important:
    sklearn can fail when all descriptions contain only stop words.
    In that case we safely return a zero matrix instead of crashing.

    For one report, the similarity matrix is [[1.0]].
    """

    n = len(reports)

    if n == 0:
        return []

    texts = [
        safe_text(
            report.get(
                "description",
                ""
            )
        )
        for report in reports
    ]

    # If there is no usable text, return a zero matrix.
    if not any(texts):

        return [
            [0.0] * n
            for _ in range(n)
        ]

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english"
        )

        matrix = vectorizer.fit_transform(
            texts
        )

        similarity_matrix = cosine_similarity(
            matrix
        )

        return similarity_matrix

    except ValueError:
        # Example:
        # "the and is of"
        # can produce an empty vocabulary after stop-word removal.

        return [
            [0.0] * n
            for _ in range(n)
        ]

    except Exception:
        return [
            [0.0] * n
            for _ in range(n)
        ]


# -------------------------------------------------------------------
# Incident type similarity
# -------------------------------------------------------------------

def normalize_incident_type(
    text
):
    """
    Normalize incident type from natural-language text.
    """

    text = safe_text(
        text
    ).lower()

    if not text:
        return "other"

    if any(
        word in text
        for word in [
            "flood",
            "flooding",
            "flooded",
            "water entered",
            "waterlogging",
            "water logging"
        ]
    ):
        return "flood"

    if any(
        word in text
        for word in [
            "landslide",
            "land slide",
            "mudslide",
            "mud slide"
        ]
    ):
        return "landslide"

    if any(
        word in text
        for word in [
            "road blockage",
            "road blocked",
            "road closed",
            "blocked road",
            "road is blocked",
            "roads blocked"
        ]
    ):
        return "road_blockage"

    if any(
        word in text
        for word in [
            "building collapse",
            "building collapsed",
            "house collapsed",
            "building has collapsed",
            "building collapse",
            "structure collapsed"
        ]
    ):
        return "building_collapse"

    if any(
        word in text
        for word in [
            "storm",
            "cyclone",
            "heavy winds",
            "strong winds",
            "high winds"
        ]
    ):
        return "storm"

    return "other"


def incident_type_similarity(
    report1,
    report2
):
    type1 = report1.get(
        "incident_type"
    )

    type2 = report2.get(
        "incident_type"
    )

    if type1 is None or type2 is None:
        return None

    if type1 == type2:
        return 1.0

    if (
        type1 == "other"
        or type2 == "other"
    ):
        return 0.5

    return 0.0


# -------------------------------------------------------------------
# Relatedness / clustering
# -------------------------------------------------------------------

def calculate_relatedness(
    report1,
    report2,
    text_similarity
):
    """
    Weighted relatedness score.

    Geographic similarity:   40%
    Temporal similarity:     20%
    Text similarity:         25%
    Incident type:            15%

    Existing project threshold is preserved.
    """

    geo = geographic_similarity(
        report1,
        report2
    )

    time = temporal_similarity(
        report1,
        report2
    )

    incident_type = incident_type_similarity(
        report1,
        report2
    )

    score = 0.0

    if geo is not None:
        score += 0.40 * geo

    if time is not None:
        score += 0.20 * time

    score += (
        0.25
        * float(text_similarity or 0.0)
    )

    if incident_type is not None:
        score += (
            0.15
            * incident_type
        )

    return score


def are_related(
    report1,
    report2,
    text_similarity
):
    """
    Two reports are considered related at score >= 0.65.
    """

    score = calculate_relatedness(
        report1,
        report2,
        text_similarity
    )

    return score >= 0.65


def cluster_reports(
    reports
):
    """
    Cluster reports using graph connectivity.

    If A is related to B and B is related to C,
    the reports form one connected cluster.

    This is intentionally retained because it allows
    multiple independent citizen reports to consolidate
    into one real-world incident.
    """

    if not reports:
        return []

    n = len(
        reports
    )

    if n == 1:
        return [
            [
                reports[0]
            ]
        ]

    text_similarity_matrix = (
        calculate_text_similarities(
            reports
        )
    )

    visited = set()
    clusters = []

    for i in range(n):

        if i in visited:
            continue

        cluster = []
        stack = [i]

        while stack:

            current = stack.pop()

            if current in visited:
                continue

            visited.add(
                current
            )

            cluster.append(
                reports[current]
            )

            for j in range(n):

                if j in visited:
                    continue

                try:
                    text_similarity = float(
                        text_similarity_matrix[
                            current
                        ][j]
                    )

                except (
                    IndexError,
                    TypeError,
                    KeyError
                ):
                    text_similarity = 0.0

                if are_related(
                    reports[current],
                    reports[j],
                    text_similarity
                ):
                    stack.append(
                        j
                    )

        clusters.append(
            cluster
        )

    return clusters


# -------------------------------------------------------------------
# Aggregation helpers
# -------------------------------------------------------------------

def max_known_value(
    reports,
    field
):
    """
    Return the maximum known numeric value for a field.
    Ignore None and invalid values.
    """

    values = []

    for report in reports:

        value = safe_non_negative_int(
            report.get(field)
        )

        if value is not None:
            values.append(
                value
            )

    if not values:
        return None

    return max(
        values
    )


def aggregate_boolean(
    reports,
    field
):
    """
    Aggregate a nullable boolean.

    True + anything -> True
    False + False/None -> False
    None + None -> None
    """

    values = [
        safe_nullable_boolean(
            report.get(field)
        )
        for report in reports
    ]

    if True in values:
        return True

    known_values = [
        value
        for value in values
        if value is not None
    ]

    if not known_values:
        return None

    if all(
        value is False
        for value in known_values
    ):
        return False

    return None


def aggregate_incident_type(
    reports
):
    """
    Select the dominant incident type.

    Specific incident types are preferred over 'other'.
    """

    incident_types = []

    for report in reports:

        incident_type = report.get(
            "incident_type"
        )

        if incident_type in ALLOWED_INCIDENT_TYPES:
            incident_types.append(
                incident_type
            )

    if not incident_types:
        return "other"

    counts = Counter(
        incident_types
    )

    specific_types = {
        incident_type: count
        for incident_type, count
        in counts.items()
        if incident_type != "other"
    }

    if specific_types:

        return max(
            specific_types,
            key=lambda x: (
                specific_types[x],
                x
            )
        )

    return "other"


# -------------------------------------------------------------------
# Coordinates / Assam validation
# -------------------------------------------------------------------

def valid_coordinates(
    latitude,
    longitude
):
    """
    Check whether latitude/longitude are valid numeric coordinates.
    """

    if (
        latitude is None
        or longitude is None
    ):
        return False

    try:

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

    except (
        TypeError,
        ValueError
    ):
        return False

    if not (
        -90 <= latitude <= 90
    ):
        return False

    if not (
        -180 <= longitude <= 180
    ):
        return False

    return True


def check_assam_coordinates(
    latitude,
    longitude
):
    """
    Reverse-geocode coordinates and determine whether
    they fall within Assam.

    Returns:
        True  -> Assam
        False -> outside Assam
        None  -> unable to determine
    """

    if not valid_coordinates(
        latitude,
        longitude
    ):
        return None

    try:

        location = geolocator.reverse(
            (
                latitude,
                longitude
            ),
            exactly_one=True,
            language="en"
        )

        if location is None:
            return None

        address = location.raw.get(
            "address",
            {}
        )

        state = safe_text(
            address.get(
                "state",
                ""
            )
        ).lower()

        return (
            state == "assam"
        )

    except Exception:
        return None


def process_location(
    report
):
    """
    Resolve report location.

    Priority:
        1. Device GPS
        2. Human-readable location text
        3. Unresolved

    All valid coordinates are retained even if Assam
    verification fails.
    """

    latitude = report.get(
        "latitude"
    )

    longitude = report.get(
        "longitude"
    )

    location_text = safe_text(
        report.get(
            "location_text"
        )
    )

    # ---------------------------------------------------------------
    # CASE 1: GPS coordinates available
    # ---------------------------------------------------------------

    if valid_coordinates(
        latitude,
        longitude
    ):

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

        in_assam = check_assam_coordinates(
            latitude,
            longitude
        )

        report["latitude"] = latitude
        report["longitude"] = longitude

        if in_assam is True:

            report["location_status"] = (
                "resolved"
            )

            report["location_source"] = (
                "device_gps"
            )

        elif in_assam is False:

            report["location_status"] = (
                "out_of_scope"
            )

            report["location_source"] = (
                "device_gps"
            )

        else:

            report["location_status"] = (
                "unresolved"
            )

            # Keep the original GPS source even when
            # Assam verification is unavailable.
            report["location_source"] = (
                "device_gps"
            )

        return report

    # ---------------------------------------------------------------
    # CASE 2: GPS unavailable, use location text
    # ---------------------------------------------------------------

    if location_text:

        query = (
            f"{location_text}, Assam, India"
        )

        try:

            location = geolocator.geocode(
                query,
                exactly_one=True
            )

            if location is not None:

                latitude = float(
                    location.latitude
                )

                longitude = float(
                    location.longitude
                )

                in_assam = check_assam_coordinates(
                    latitude,
                    longitude
                )

                report["latitude"] = latitude
                report["longitude"] = longitude

                if in_assam is True:

                    report["location_status"] = (
                        "resolved"
                    )

                    report["location_source"] = (
                        "geocoded"
                    )

                elif in_assam is False:

                    report["location_status"] = (
                        "out_of_scope"
                    )

                    report["location_source"] = (
                        "geocoded"
                    )

                else:

                    report["location_status"] = (
                        "unresolved"
                    )

                    report["location_source"] = (
                        "geocoded"
                    )

                return report

        except Exception:
            pass

    # ---------------------------------------------------------------
    # CASE 3: No usable location
    # ---------------------------------------------------------------

    report["latitude"] = None
    report["longitude"] = None
    report["location_status"] = (
        "unresolved"
    )
    report["location_source"] = (
        "unresolved"
    )

    return report


# -------------------------------------------------------------------
# Natural-language understanding
# -------------------------------------------------------------------

def extract_number(
    text,
    keywords
):
    """
    Extract a number associated with a phrase.

    Example:
        "20 people affected" -> 20
        "5 injured people"   -> 5

    The generic 'people' keyword is intentionally handled
    more carefully to avoid stealing numbers from unrelated
    phrases.
    """

    text = safe_text(
        text
    ).lower()

    if not text:
        return None

    for keyword in keywords:

        keyword = safe_text(
            keyword
        )

        if not keyword:
            continue

        if keyword == "people":

            pattern = (
                r"(?:around|about|approximately)?"
                r"\s*(\d+)\s+people"
                r"(?!\s+(?:are\s+)?"
                r"(?:trapped|stranded|injured))"
            )

        else:

            escaped_keyword = re.escape(
                keyword
            )

            pattern = (
                rf"(?:around|about|approximately)?"
                rf"\s*(\d+)\s+"
                rf"{escaped_keyword}\b"
            )

        match = re.search(
            pattern,
            text
        )

        if match:

            try:
                return int(
                    match.group(1)
                )
            except (
                TypeError,
                ValueError
            ):
                pass

    return None


def extract_people_trapped(
    text
):
    """
    Determine whether people are trapped/stranded.
    """

    text = safe_text(
        text
    ).lower()

    if not text:
        return None

    negative_words = [
        "no one trapped",
        "nobody trapped",
        "no people trapped",
        "not trapped",
        "no one is trapped",
        "nobody is trapped"
    ]

    if any(
        phrase in text
        for phrase in negative_words
    ):
        return False

    positive_words = [
        "trapped",
        "stranded",
        "unable to escape",
        "unable to leave"
    ]

    if any(
        phrase in text
        for phrase in positive_words
    ):
        return True

    return None


def extract_medical_emergency(
    text
):
    """
    Determine whether a medical emergency is described.
    """

    text = safe_text(
        text
    ).lower()

    if not text:
        return None

    negative_words = [
        "no medical emergency",
        "no medical help needed",
        "medical help not needed",
        "no ambulance needed"
    ]

    if any(
        phrase in text
        for phrase in negative_words
    ):
        return False

    positive_words = [
        "medical emergency",
        "medical help needed",
        "ambulance needed",
        "ambulance required",
        "critical patient",
        "seriously injured",
        "urgent medical help",
        "medical assistance needed"
    ]

    if any(
        phrase in text
        for phrase in positive_words
    ):
        return True

    return None


def extract_trapped_people(
    text
):
    """
    Extract the number of trapped/stranded people.
    """

    text = safe_text(
        text
    ).lower()

    if not text:
        return None

    patterns = [

        # "20 people are trapped"
        r"(?:around|about|approximately)?"
        r"\s*(\d+)\s+people"
        r"\s+(?:are\s+)?trapped",

        # "10 persons are trapped"
        r"(?:around|about|approximately)?"
        r"\s*(\d+)\s+persons"
        r"\s+(?:are\s+)?trapped",

        # "trapped around 10 people"
        r"trapped\s+"
        r"(?:around|about|approximately)?"
        r"\s*(\d+)\s+people",

        # "trapped 10 people"
        r"trapped\s+(\d+)\s+people",

        # "10 people are stranded"
        r"(?:around|about|approximately)?"
        r"\s*(\d+)\s+people"
        r"\s+(?:are\s+)?stranded",

        # "10 persons are stranded"
        r"(?:around|about|approximately)?"
        r"\s*(\d+)\s+persons"
        r"\s+(?:are\s+)?stranded"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            try:
                return int(
                    match.group(1)
                )
            except (
                TypeError,
                ValueError
            ):
                pass

    return None


def extract_severity_indicators(
    report
):
    """
    Generate Module 2 severity indicators used by
    downstream priority calculation.
    """

    indicators = []

    people_trapped = safe_nullable_boolean(
        report.get(
            "people_trapped"
        )
    )

    injured_people = safe_non_negative_int(
        report.get(
            "injured_people"
        )
    )

    trapped_people = safe_non_negative_int(
        report.get(
            "trapped_people"
        )
    )

    medical_emergency = safe_nullable_boolean(
        report.get(
            "medical_emergency"
        )
    )

    # A numeric trapped count is itself evidence that
    # people are trapped.
    if (
        people_trapped is True
        or (
            trapped_people is not None
            and trapped_people > 0
        )
    ):
        indicators.append(
            "people_trapped"
        )

    if (
        injured_people is not None
        and injured_people > 0
    ):
        indicators.append(
            "injuries_reported"
        )

    if medical_emergency is True:
        indicators.append(
            "medical_emergency"
        )

    description = safe_text(
        report.get(
            "description",
            ""
        )
    ).lower()

    if any(
        word in description
        for word in [
            "house",
            "houses",
            "residential area",
            "home",
            "homes"
        ]
    ):
        indicators.append(
            "residential_area_affected"
        )

    return indicators


def understand_report(
    report
):
    """
    Stage 1 of Module 2.

    Understand and normalize one raw report before
    location processing and clustering.
    """

    if not isinstance(
        report,
        dict
    ):
        raise TypeError(
            "Each report must be a dictionary"
        )

    description = safe_text(
        report.get(
            "description",
            ""
        )
    )

    # ---------------------------------------------------------------
    # Extract values from natural language
    # ---------------------------------------------------------------

    extracted_incident_type = (
        normalize_incident_type(
            description
        )
    )

    extracted_affected = extract_number(
        description,
        [
            "people affected",
            "persons affected",
            "affected people",
            "affected persons",
            "people"
        ]
    )

    extracted_injured = extract_number(
        description,
        [
            "injured people",
            "injured persons",
            "people injured",
            "persons injured",
            "injured"
        ]
    )

    extracted_trapped = (
        extract_trapped_people(
            description
        )
    )

    extracted_people_trapped = (
        extract_people_trapped(
            description
        )
    )

    extracted_medical = (
        extract_medical_emergency(
            description
        )
    )

    # ---------------------------------------------------------------
    # Module 1 values have priority
    # ---------------------------------------------------------------

    raw_incident_type = report.get(
        "incident_type"
    )

    if raw_incident_type is not None:

        incident_type = normalize_incident_type(
            raw_incident_type
        )

        # If Module 1 already provides a valid normalized
        # incident type, retain it directly.
        normalized_raw_type = safe_text(
            raw_incident_type
        ).lower()

        if normalized_raw_type in ALLOWED_INCIDENT_TYPES:
            incident_type = normalized_raw_type

    else:

        incident_type = (
            extracted_incident_type
        )

    affected_people = safe_non_negative_int(
        report.get(
            "affected_people"
        )
    )

    if affected_people is None:
        affected_people = extracted_affected

    injured_people = safe_non_negative_int(
        report.get(
            "injured_people"
        )
    )

    if injured_people is None:
        injured_people = extracted_injured

    trapped_people = safe_non_negative_int(
        report.get(
            "trapped_people"
        )
    )

    if trapped_people is None:
        trapped_people = extracted_trapped

    people_trapped = safe_nullable_boolean(
        report.get(
            "people_trapped"
        )
    )

    if people_trapped is None:
        people_trapped = (
            extracted_people_trapped
        )

    medical_emergency = safe_nullable_boolean(
        report.get(
            "medical_emergency"
        )
    )

    if medical_emergency is None:
        medical_emergency = (
            extracted_medical
        )

    vulnerable_people = safe_non_negative_int(
        report.get(
            "vulnerable_people"
        )
    )

    # ---------------------------------------------------------------
    # Reconcile trapped count and trapped boolean
    # ---------------------------------------------------------------

    # If a report explicitly/implicitly says that a positive
    # number of people are trapped, the boolean must reflect it.
    if (
        trapped_people is not None
        and trapped_people > 0
    ):
        people_trapped = True

    # If an explicit negative statement says nobody is trapped
    # and no positive count exists, retain False.
    if (
        trapped_people == 0
        and people_trapped is None
    ):
        people_trapped = False

    # ---------------------------------------------------------------
    # Build normalized report
    # ---------------------------------------------------------------

    processed_report = {
        **report,

        "description":
            description,

        "incident_type":
            incident_type,

        "affected_people":
            affected_people,

        "injured_people":
            injured_people,

        "people_trapped":
            people_trapped,

        "trapped_people":
            trapped_people,

        "medical_emergency":
            medical_emergency,

        "vulnerable_people":
            vulnerable_people
    }

    processed_report[
        "severity_indicators"
    ] = extract_severity_indicators(
        processed_report
    )

    return processed_report


# -------------------------------------------------------------------
# Cluster aggregation
# -------------------------------------------------------------------

def aggregate_location(
    reports
):
    """
    Select a representative resolved location.

    Preference:
        1. device GPS
        2. geocoded coordinates
        3. unresolved
    """

    # ---------------------------------------------------------------
    # First preference: device GPS
    # ---------------------------------------------------------------

    for report in reports:

        if (
            report.get(
                "location_status"
            ) == "resolved"
            and report.get(
                "location_source"
            ) == "device_gps"
            and valid_coordinates(
                report.get(
                    "latitude"
                ),
                report.get(
                    "longitude"
                )
            )
        ):

            return {
                "latitude": float(
                    report["latitude"]
                ),

                "longitude": float(
                    report["longitude"]
                ),

                "location_status":
                    "resolved",

                "location_source":
                    "device_gps"
            }

    # ---------------------------------------------------------------
    # Second preference: geocoded
    # ---------------------------------------------------------------

    for report in reports:

        if (
            report.get(
                "location_status"
            ) == "resolved"
            and report.get(
                "location_source"
            ) == "geocoded"
            and valid_coordinates(
                report.get(
                    "latitude"
                ),
                report.get(
                    "longitude"
                )
            )
        ):

            return {
                "latitude": float(
                    report["latitude"]
                ),

                "longitude": float(
                    report["longitude"]
                ),

                "location_status":
                    "resolved",

                "location_source":
                    "geocoded"
            }

    # ---------------------------------------------------------------
    # No valid location
    # ---------------------------------------------------------------

    return {
        "latitude": None,
        "longitude": None,
        "location_status":
            "unresolved",
        "location_source":
            "unresolved"
    }


def aggregate_cluster(
    reports,
    candidate_id=None
):
    """
    Convert one cluster of related reports into
    one consolidated incident candidate.

    candidate_id is retained only for backward compatibility.
    It is not included in the Module 2 output contract.
    """

    if not reports:
        raise ValueError(
            "Cannot aggregate an empty cluster"
        )

    location = aggregate_location(
        reports
    )

    # ---------------------------------------------------------------
    # Source report IDs
    # ---------------------------------------------------------------

    source_report_ids = []

    for report in reports:

        report_id = report.get(
            "report_id"
        )

        if (
            report_id is not None
            and report_id not in source_report_ids
        ):
            source_report_ids.append(
                report_id
            )

    # ---------------------------------------------------------------
    # Location text
    # ---------------------------------------------------------------

    location_text = None

    for report in reports:

        value = safe_text(
            report.get(
                "location_text"
            )
        )

        if value:

            location_text = value
            break

    # ---------------------------------------------------------------
    # Earliest report timestamp
    # ---------------------------------------------------------------

    timestamps = []

    for report in reports:

        timestamp = report.get(
            "submitted_at"
        )

        parsed = parse_timestamp(
            timestamp
        )

        if parsed is not None:

            timestamps.append(
                (
                    parsed,
                    timestamp
                )
            )

    if timestamps:

        timestamps.sort(
            key=lambda item: item[0]
        )

        reported_at = timestamps[0][1]

    else:

        reported_at = None

    # ---------------------------------------------------------------
    # Severity indicators
    # ---------------------------------------------------------------

    severity_indicators = []

    for report in reports:

        indicators = report.get(
            "severity_indicators",
            []
        )

        if not isinstance(
            indicators,
            list
        ):
            continue

        for indicator in indicators:

            if (
                indicator not in
                severity_indicators
            ):
                severity_indicators.append(
                    indicator
                )

    # ---------------------------------------------------------------
    # Numeric aggregates
    # ---------------------------------------------------------------

    affected_people = max_known_value(
        reports,
        "affected_people"
    )

    injured_people = max_known_value(
        reports,
        "injured_people"
    )

    trapped_people = max_known_value(
        reports,
        "trapped_people"
    )

    vulnerable_people = max_known_value(
        reports,
        "vulnerable_people"
    )

    # ---------------------------------------------------------------
    # Boolean aggregates
    # ---------------------------------------------------------------

    people_trapped = aggregate_boolean(
        reports,
        "people_trapped"
    )

    medical_emergency = aggregate_boolean(
        reports,
        "medical_emergency"
    )

    # Numeric trapped count is stronger evidence than
    # an unknown boolean.
    if (
        trapped_people is not None
        and trapped_people > 0
    ):
        people_trapped = True

    # ---------------------------------------------------------------
    # Description
    # ---------------------------------------------------------------

    descriptions = [
        safe_text(
            report.get(
                "description",
                ""
            )
        )
        for report in reports
    ]

    descriptions = [
        text
        for text in descriptions
        if text
    ]

    if descriptions:

        # Preserve the longest description because it generally
        # contains the most context.
        description = max(
            descriptions,
            key=len
        )

    else:

        description = ""

    # ---------------------------------------------------------------
    # Consolidated candidate
    # ---------------------------------------------------------------

    candidate = {

        "source_report_ids":
            source_report_ids,

        "incident_type":
            aggregate_incident_type(
                reports
            ),

        "description":
            description,

        "location_text":
            location_text,

        "latitude":
            location["latitude"],

        "longitude":
            location["longitude"],

        "location_status":
            location["location_status"],

        "location_source":
            location["location_source"],

        "affected_people":
            affected_people,

        "injured_people":
            injured_people,

        "people_trapped":
            people_trapped,

        "trapped_people":
            trapped_people,

        "medical_emergency":
            medical_emergency,

        "vulnerable_people":
            vulnerable_people,

        "severity_indicators":
            severity_indicators,

        "reported_at":
            reported_at,
    }

    # Ensure indicators also reflect the final
    # consolidated values.
    candidate[
        "severity_indicators"
    ] = extract_severity_indicators(
        candidate
    )

    return candidate


# -------------------------------------------------------------------
# Candidate validation
# -------------------------------------------------------------------

def validate_incident_candidate(
    candidate
):
    """
    Validate the structure and values of one
    consolidated Module 2 candidate.
    """

    if not isinstance(
        candidate,
        dict
    ):
        return False

    # ---------------------------------------------------------------
    # Incident type
    # ---------------------------------------------------------------

    if (
        candidate.get(
            "incident_type"
        )
        not in ALLOWED_INCIDENT_TYPES
    ):
        return False

    # ---------------------------------------------------------------
    # Numeric fields
    # ---------------------------------------------------------------

    numeric_fields = [
        "affected_people",
        "injured_people",
        "trapped_people",
        "vulnerable_people"
    ]

    for field in numeric_fields:

        value = candidate.get(
            field
        )

        if value is not None:

            if isinstance(
                value,
                bool
            ):
                return False

            try:
                value = int(
                    value
                )

            except (
                TypeError,
                ValueError
            ):
                return False

            if value < 0:
                return False

    # ---------------------------------------------------------------
    # Boolean fields
    # ---------------------------------------------------------------

    boolean_fields = [
        "people_trapped",
        "medical_emergency"
    ]

    for field in boolean_fields:

        value = candidate.get(
            field
        )

        if (
            value is not None
            and not isinstance(
                value,
                bool
            )
        ):
            return False

    # ---------------------------------------------------------------
    # Coordinates
    # ---------------------------------------------------------------

    latitude = candidate.get(
        "latitude"
    )

    longitude = candidate.get(
        "longitude"
    )

    if (
        latitude is not None
        or longitude is not None
    ):

        if not valid_coordinates(
            latitude,
            longitude
        ):
            return False

    # ---------------------------------------------------------------
    # Location status
    # ---------------------------------------------------------------

    valid_location_statuses = {
        "resolved",
        "unresolved",
        "out_of_scope"
    }

    if (
        candidate.get(
            "location_status"
        )
        not in valid_location_statuses
    ):
        return False

    # ---------------------------------------------------------------
    # Location source
    # ---------------------------------------------------------------

    valid_location_sources = {
        "device_gps",
        "geocoded",
        "unresolved"
    }

    if (
        candidate.get(
            "location_source"
        )
        not in valid_location_sources
    ):
        return False

    # ---------------------------------------------------------------
    # Source report IDs
    # ---------------------------------------------------------------

    source_report_ids = candidate.get(
        "source_report_ids"
    )

    if not isinstance(
        source_report_ids,
        list
    ):
        return False

    # ---------------------------------------------------------------
    # Severity indicators
    # ---------------------------------------------------------------

    if not isinstance(
        candidate.get(
            "severity_indicators"
        ),
        list
    ):
        return False

    return True


# -------------------------------------------------------------------
# Main Module 2 pipeline
# -------------------------------------------------------------------

def process_reports(
    raw_reports: list[dict]
) -> list[dict]:
    """
    Main Module 2 pipeline.

    Flow:

        Raw Reports
            ↓
        Understand Reports
            ↓
        Process Locations
            ↓
        Cluster Related Reports
            ↓
        Aggregate Each Cluster
            ↓
        Validate Candidates
            ↓
        Module 2 Output
    """

    if not isinstance(
        raw_reports,
        list
    ):
        raise TypeError(
            "raw_reports must be a list"
        )

    if not raw_reports:
        return []

    processed_reports = []

    for report in raw_reports:

        if not isinstance(
            report,
            dict
        ):
            raise TypeError(
                "Every report must be a dictionary"
            )

        # -----------------------------------------------------------
        # Stage 1: Understand report
        # -----------------------------------------------------------

        processed_report = (
            understand_report(
                report
            )
        )

        # -----------------------------------------------------------
        # Stage 2: Process location
        # -----------------------------------------------------------

        processed_report = (
            process_location(
                processed_report
            )
        )

        processed_reports.append(
            processed_report
        )

    # ---------------------------------------------------------------
    # Stage 3: Cluster related reports
    # ---------------------------------------------------------------

    clusters = cluster_reports(
        processed_reports
    )

    # ---------------------------------------------------------------
    # Stage 4: Aggregate clusters
    # ---------------------------------------------------------------

    incident_candidates = []

    for cluster in clusters:

        candidate = aggregate_cluster(
            cluster
        )

        # -----------------------------------------------------------
        # Stage 5: Validate candidate
        # -----------------------------------------------------------

        if not validate_incident_candidate(
            candidate
        ):

            raise ValueError(
                "Invalid incident candidate: "
                f"{candidate}"
            )

        incident_candidates.append(
            candidate
        )

    return incident_candidates


# -------------------------------------------------------------------
# Local test
# -------------------------------------------------------------------

if __name__ == "__main__":

    raw_reports = [

        {
            "report_id": "R001",
            "source_type": "citizen",
            "location_text": "Dibrugarh, Assam",
            "latitude": 27.4728,
            "longitude": 94.9120,
            "description": (
                "Flood water has entered houses "
                "and 20 people are trapped."
            ),
            "affected_people": 20,
            "injured_people": 1,
            "people_trapped": True,
            "medical_emergency": True,
            "submitted_at":
                "2026-09-06T10:00:15"
        },

        {
            "report_id": "R002",
            "source_type": "citizen",
            "location_text": "Dibrugarh, Assam",
            "latitude": 27.4732,
            "longitude": 94.9124,
            "description": (
                "Flooding has trapped around "
                "10 people near the houses."
            ),
            "affected_people": 10,
            "injured_people": None,
            "people_trapped": True,
            "medical_emergency": None,
            "submitted_at":
                "2026-09-06T10:01:02"
        },

        {
            "report_id": "R003",
            "source_type": "citizen",
            "location_text": "Dibrugarh, Assam",
            "latitude": 27.4730,
            "longitude": 94.9122,
            "description": (
                "Several families are trapped "
                "because of flood water."
            ),
            "affected_people": None,
            "injured_people": None,
            "people_trapped": True,
            "medical_emergency": None,
            "submitted_at":
                "2026-09-06T10:03:00"
        }
    ]

    result = process_reports(
        raw_reports
    )

    print(
        "\n========================================"
    )

    print(
        "MODULE 2 TEST RESULT"
    )

    print(
        "========================================"
    )

    print(
        "Number of incident candidates:",
        len(result)
    )

    for candidate in result:

        print(
            "\nIncident Candidate:"
        )

        print(
            "Incident Type:",
            candidate[
                "incident_type"
            ]
        )

        print(
            "Affected People:",
            candidate[
                "affected_people"
            ]
        )

        print(
            "Injured People:",
            candidate[
                "injured_people"
            ]
        )

        print(
            "Trapped People:",
            candidate[
                "trapped_people"
            ]
        )

        print(
            "People Trapped:",
            candidate[
                "people_trapped"
            ]
        )

        print(
            "Medical Emergency:",
            candidate[
                "medical_emergency"
            ]
        )

        print(
            "Location:",
            candidate[
                "latitude"
            ],
            candidate[
                "longitude"
            ]
        )

        print(
            "Source Reports:",
            candidate[
                "source_report_ids"
            ]
        )

        print(
            "Severity Indicators:",
            candidate[
                "severity_indicators"
            ]
        )

    print(
        "\n========================================"
    )