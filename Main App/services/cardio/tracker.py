"""
Cardio Session Tracker Engine
=============================
Handles the live tracking lifecycle of a running or walking activity:
- Start, Pause, Resume, and Finish.
- Accurate calculation of total elapsed time vs moving time.
- Processing incoming GPS samples and rejecting noise during pause.
- Building the ordered route coordinate list for rendering polyline.
"""
import time
from typing import Dict, Any, List, Optional
from services.cardio.geolocation import (
    haversine_distance,
    is_valid_gps_point,
    calculate_pace,
    calculate_speed_kmh,
    format_duration,
    DEFAULT_MAX_ACCURACY_METERS
)


class CardioTracker:
    def __init__(self, activity_type: str = "Running", max_accuracy_meters: float = DEFAULT_MAX_ACCURACY_METERS):
        self.activity_type = activity_type
        self.max_accuracy_meters = max_accuracy_meters
        self.status: str = "idle"  # 'idle', 'tracking', 'paused', 'completed'
        
        self.start_timestamp: float = 0.0
        self.pause_timestamp: float = 0.0
        self.total_paused_seconds: float = 0.0
        self.finish_timestamp: float = 0.0

        self.distance_meters: float = 0.0
        self.route_points: List[Dict[str, Any]] = []
        self.last_valid_point: Optional[Dict[str, Any]] = None

        # Metrics cache
        self.current_speed_kmh: float = 0.0
        self.average_speed_kmh: float = 0.0
        self.current_pace_str: str = "--:-- /km"
        self.average_pace_str: str = "--:-- /km"
        self.average_pace_sec: float = 0.0

    def start(self) -> None:
        """Start or restart the cardio activity."""
        self.status = "tracking"
        self.start_timestamp = time.time()
        self.pause_timestamp = 0.0
        self.total_paused_seconds = 0.0
        self.distance_meters = 0.0
        self.route_points = []
        self.last_valid_point = None

    def pause(self) -> None:
        """Pause active tracking. While paused, incoming GPS coordinates do not add distance."""
        if self.status == "tracking":
            self.status = "paused"
            self.pause_timestamp = time.time()

    def resume(self) -> None:
        """Resume active tracking."""
        if self.status == "paused":
            now = time.time()
            if self.pause_timestamp > 0:
                self.total_paused_seconds += (now - self.pause_timestamp)
            self.pause_timestamp = 0.0
            self.status = "tracking"

    def finish(self) -> None:
        """Finish the activity and seal metrics."""
        if self.status in ("tracking", "paused"):
            if self.status == "paused" and self.pause_timestamp > 0:
                self.total_paused_seconds += (time.time() - self.pause_timestamp)
            self.status = "completed"
            self.finish_timestamp = time.time()

    def get_elapsed_seconds(self) -> float:
        """Total time since start button was pressed."""
        if self.start_timestamp == 0:
            return 0.0
        if self.status == "completed":
            return max(0.0, self.finish_timestamp - self.start_timestamp)
        return max(0.0, time.time() - self.start_timestamp)

    def get_moving_seconds(self) -> float:
        """Active moving time (total elapsed minus paused time)."""
        if self.start_timestamp == 0:
            return 0.0
        now = self.finish_timestamp if self.status == "completed" else time.time()
        current_paused = 0.0
        if self.status == "paused" and self.pause_timestamp > 0:
            current_paused = now - self.pause_timestamp
        moving = (now - self.start_timestamp) - (self.total_paused_seconds + current_paused)
        return max(0.0, moving)

    def add_gps_sample(self, lat: float, lng: float, accuracy: float, timestamp: Optional[float] = None) -> bool:
        """
        Process a new GPS reading from browser geolocation.
        Returns True if accepted and appended to route.
        """
        if self.status != "tracking":
            return False

        ts = timestamp if timestamp else time.time()

        sample_info = {
            "latitude": lat,
            "longitude": lng,
            "accuracy": accuracy,
            "current_timestamp": ts
        }

        # Validate with filter
        valid, reason = is_valid_gps_point(
            lat=lat,
            lng=lng,
            accuracy=accuracy,
            last_point=self.last_valid_point,
            max_accuracy_meters=self.max_accuracy_meters
        )

        if not valid:
            return False

        # If we have a prior valid point, accumulate distance and instant speed
        if self.last_valid_point:
            delta_dist = haversine_distance(
                self.last_valid_point["latitude"],
                self.last_valid_point["longitude"],
                lat,
                lng
            )
            self.distance_meters += delta_dist

            dt = ts - self.last_valid_point["timestamp"]
            if dt > 0:
                inst_speed_mps = delta_dist / dt
                self.current_speed_kmh = round(inst_speed_mps * 3.6, 1)
                _, self.current_pace_str = calculate_pace(dt, delta_dist)

        # Update last valid point
        new_point = {
            "sequence_number": len(self.route_points) + 1,
            "latitude": lat,
            "longitude": lng,
            "accuracy": accuracy,
            "timestamp": ts,
            "speed_kmh": self.current_speed_kmh
        }
        self.route_points.append(new_point)
        self.last_valid_point = {
            "latitude": lat,
            "longitude": lng,
            "accuracy": accuracy,
            "timestamp": ts
        }

        # Recalculate average pace and average speed
        moving_sec = self.get_moving_seconds()
        self.average_speed_kmh = calculate_speed_kmh(moving_sec, self.distance_meters)
        self.average_pace_sec, self.average_pace_str = calculate_pace(moving_sec, self.distance_meters)

        return True

    def get_summary(self) -> Dict[str, Any]:
        """Return structured summary of the cardio session."""
        moving_sec = self.get_moving_seconds()
        elapsed_sec = self.get_elapsed_seconds()
        distance_km = round(self.distance_meters / 1000.0, 2)

        return {
            "activity_type": self.activity_type,
            "status": self.status,
            "distance_meters": round(self.distance_meters, 1),
            "distance_km": distance_km,
            "elapsed_seconds": int(elapsed_sec),
            "moving_seconds": int(moving_sec),
            "elapsed_formatted": format_duration(elapsed_sec),
            "moving_formatted": format_duration(moving_sec),
            "current_speed_kmh": self.current_speed_kmh,
            "average_speed_kmh": self.average_speed_kmh,
            "current_pace": self.current_pace_str,
            "average_pace": self.average_pace_str,
            "average_pace_sec_per_km": self.average_pace_sec,
            "route_points_count": len(self.route_points),
            "route_coordinates": [[p["latitude"], p["longitude"]] for p in self.route_points]
        }
