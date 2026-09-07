"""
Cardio Geolocation & Mathematical Processing Engine
===================================================
Provides:
- Haversine formula for exact geodesic distance.
- GPS quality filtering (accuracy threshold and impossible jump rejection).
- Instantaneous and average pace calculation (mm:ss /km).
- Speed calculation (km/h).
"""
import math
from typing import Optional, Tuple, Dict, Any

DEFAULT_MAX_ACCURACY_METERS = 50.0  # Points with accuracy worse than 50m are rejected
MAX_REALISTIC_SPEED_MPS = 13.0     # ~46.8 km/h max realistic running/sprinting speed


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula. Returns distance in meters.
    """
    r_earth_meters = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return r_earth_meters * c


def is_valid_gps_point(
    lat: float,
    lng: float,
    accuracy: float,
    last_point: Optional[Dict[str, Any]] = None,
    max_accuracy_meters: float = DEFAULT_MAX_ACCURACY_METERS
) -> Tuple[bool, str]:
    """
    Filter GPS points to reject low-accuracy readings and impossible jumps.
    Returns (is_valid, reason).
    """
    if lat is None or lng is None:
        return False, "Coordinates cannot be None"

    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        return False, "Invalid coordinate ranges"

    if accuracy is not None and accuracy > max_accuracy_meters:
        return False, f"GPS accuracy too low ({accuracy:.1f}m > {max_accuracy_meters}m)"

    if last_point is not None:
        prev_lat = last_point.get("latitude")
        prev_lng = last_point.get("longitude")
        prev_time = last_point.get("timestamp", 0)
        curr_time = last_point.get("current_timestamp", 0)

        if prev_lat is not None and prev_lng is not None:
            dist = haversine_distance(prev_lat, prev_lng, lat, lng)
            # If distance is under 1 meter, it's stationary drift
            if dist < 0.5:
                return False, "Stationary GPS noise (< 0.5m)"

            if curr_time and prev_time and curr_time > prev_time:
                dt = curr_time - prev_time
                speed_mps = dist / dt
                if speed_mps > MAX_REALISTIC_SPEED_MPS:
                    return False, f"Impossible speed jump ({speed_mps * 3.6:.1f} km/h)"

    return True, "Valid point"


def calculate_pace(moving_seconds: float, distance_meters: float) -> Tuple[float, str]:
    """
    Calculate pace in seconds per kilometer and return formatted 'MM:SS /km'.
    If distance is too small (< 20m), returns (0.0, '--:-- /km').
    """
    if distance_meters < 20.0 or moving_seconds <= 0:
        return 0.0, "--:-- /km"

    distance_km = distance_meters / 1000.0
    sec_per_km = moving_seconds / distance_km

    # Cap unrealistic pace (over 30 min/km)
    if sec_per_km > 1800.0:
        return 1800.0, "30:00+ /km"

    mins = int(sec_per_km // 60)
    secs = int(sec_per_km % 60)
    return sec_per_km, f"{mins:02d}:{secs:02d} /km"


def calculate_speed_kmh(moving_seconds: float, distance_meters: float) -> float:
    """
    Calculate average speed in kilometers per hour.
    """
    if moving_seconds <= 0 or distance_meters <= 0:
        return 0.0
    speed_mps = distance_meters / moving_seconds
    return round(speed_mps * 3.6, 2)


def format_duration(seconds: float) -> str:
    """
    Format seconds into HH:MM:SS or MM:SS.
    """
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
