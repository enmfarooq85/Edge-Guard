import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TelemetryEvent(BaseModel):
    event_id: str
    timestamp: float = Field(default_factory=time.time)
    prompt: str
    selected_route: str
    decision_code: str
    reason: str
    policy_passed: bool
    local_latency_ms: Optional[float] = None
    cloud_latency_ms: Optional[float] = None
    total_latency_ms: float
    local_success: Optional[bool] = None
    cloud_success: Optional[bool] = None
    schema_valid: Optional[bool] = None
    final_output: str

class TelemetryLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryLogger, cls).__new__(cls)
            cls._instance.events: List[TelemetryEvent] = []
        return cls._instance

    def log_event(self, event: TelemetryEvent) -> None:
        """Appends a new execution event to the in-memory telemetry log."""
        self.events.append(event)

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Returns all logged telemetry events as dictionaries."""
        return [e.model_dump() for e in self.events]

    def clear(self) -> None:
        """Clears all logged telemetry events (useful between benchmark runs)."""
        self.events.clear()

    def get_summary_stats(self) -> Dict[str, Any]:
        """Calculates runtime stats across all recorded events."""
        if not self.events:
            return {
                "total_requests": 0,
                "local_routes": 0,
                "cloud_routes": 0,
                "degrade_routes": 0,
                "avg_latency_ms": 0.0
            }

        total = len(self.events)
        local_cnt = sum(1 for e in self.events if e.selected_route == "LOCAL")
        cloud_cnt = sum(1 for e in self.events if e.selected_route == "CLOUD")
        degrade_cnt = sum(1 for e in self.events if e.selected_route == "DEGRADE")
        avg_lat = sum(e.total_latency_ms for e in self.events) / total

        return {
            "total_requests": total,
            "local_routes": local_cnt,
            "cloud_routes": cloud_cnt,
            "degrade_routes": degrade_cnt,
            "avg_latency_ms": round(avg_lat, 2)
        }