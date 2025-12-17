"""data processing"""

from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List, NamedTuple
from collections import defaultdict


class DeviceReading(NamedTuple):
    device_id: str
    device_type: str
    timestamp: float
    value: Dict[str, Any]
    signal_strength: int = 100
    status: str = "online"
    issue: str = "none"
    response_time_ms: int = 50


@dataclass
class AnalyticsResult:
    metric_name: str
    value: Any
    timestamp: float
    device_count: int
    
    def __str__(self):
        return f"{self.metric_name}: {self.value} (from {self.device_count} devices)"


def make_reading(raw):
    """raw dict -> DeviceReading"""
    return DeviceReading(
        device_id=raw.get("device_id", "unknown"),
        device_type=raw.get("type", "GENERIC"),
        timestamp=raw.get("timestamp") or datetime.now().timestamp(),
        value=raw.get("payload", {}),
        signal_strength=raw.get("signal_strength", 100),
        status=raw.get("status", "online"),
        issue=raw.get("issue", "none"),
        response_time_ms=raw.get("response_time_ms", 50)
    )


def is_high_temp(r, thresh=30.0):
    if r.device_type != "THERMOSTAT":
        return False
    return r.value.get("current_temp", 0) > thresh

def is_low_batt(r, thresh=10.0):
    if r.device_type != "CAMERA":
        return False
    return r.value.get("battery_level", 100) < thresh

def has_motion(r):
    return r.device_type == "CAMERA" and r.value.get("motion_detected", False)

def has_issue(r):
    """Check if reading has any issue"""
    return r.issue != "none"


def get_critical(readings):
    """Filter for critical events using functional filter (not imperative loops)"""
    return list(filter(
        lambda r: is_high_temp(r) or is_low_batt(r) or has_motion(r),
        readings
    ))


def avg_temp(readings):
    """Calculate average temperature using functools.reduce"""
    thermos = list(filter(lambda r: r.device_type == "THERMOSTAT", readings))
    if not thermos:
        return AnalyticsResult("Average Temperature", None, datetime.now().timestamp(), 0)
    
    # Using reduce to sum all temperatures (functional programming requirement)
    total_temp = reduce(
        lambda acc, r: acc + r.value.get("current_temp", 0),
        thermos,
        0
    )
    
    return AnalyticsResult(
        "Average Temperature",
        round(total_temp / len(thermos), 2),
        datetime.now().timestamp(),
        len(thermos)
    )


def total_energy(readings):
    """Calculate total energy consumption using functools.reduce"""
    # Filter for bulbs that are on (functional programming)
    on_bulbs = list(filter(
        lambda r: r.device_type == "BULB" and r.value.get("is_on"),
        readings
    ))
    
    if len(on_bulbs) == 0:
        return AnalyticsResult("Total Energy Consumption", 0.0, datetime.now().timestamp(), 0)
    
    # Using reduce to calculate total watts (functional programming requirement)
    # Assume 10W max per bulb, scaled by brightness
    total_watts = reduce(
        lambda acc, b: acc + (b.value.get("brightness", 0) / 100) * 10,
        on_bulbs,
        0
    )
    
    return AnalyticsResult(
        "Total Energy Consumption",
        round(total_watts, 2),
        datetime.now().timestamp(),
        len(on_bulbs)
    )


def avg_battery(readings):
    """Calculate average battery level using functools.reduce"""
    cams = list(filter(lambda r: r.device_type == "CAMERA", readings))
    if not cams:
        return AnalyticsResult("Average Battery Level", None, datetime.now().timestamp(), 0)
    
    # Using reduce to sum battery levels (functional programming requirement)
    total_battery = reduce(
        lambda acc, c: acc + c.value.get("battery_level", 0),
        cams,
        0
    )
    
    return AnalyticsResult(
        "Average Battery Level",
        round(total_battery / len(cams), 2),
        datetime.now().timestamp(),
        len(cams)
    )


def count_devices(readings):
    """Count unique active devices using functional map"""
    # Using map to extract device_ids, then set for uniqueness
    unique_ids = set(map(lambda r: r.device_id, readings))
    n = len(unique_ids)
    return AnalyticsResult("Active Devices", n, datetime.now().timestamp(), n)


def avg_signal(readings):
    """Calculate average signal strength across all devices"""
    if not readings:
        return AnalyticsResult("Average Signal Strength", None, datetime.now().timestamp(), 0)
    
    total = sum(r.signal_strength for r in readings)
    return AnalyticsResult(
        "Average Signal Strength",
        round(total / len(readings), 1),
        datetime.now().timestamp(),
        len(readings)
    )


def avg_response_time(readings):
    """Calculate average response time"""
    if not readings:
        return AnalyticsResult("Average Response Time", None, datetime.now().timestamp(), 0)
    
    total = sum(r.response_time_ms for r in readings)
    return AnalyticsResult(
        "Average Response Time",
        f"{round(total / len(readings), 1)}ms",
        datetime.now().timestamp(),
        len(readings)
    )


def issue_breakdown(readings):
    """Get breakdown of issues by type"""
    issues = defaultdict(int)
    for r in readings:
        if r.issue != "none":
            issues[r.issue] += 1
    return dict(issues)


def device_health_score(readings):
    """Calculate overall health score (0-100)"""
    if not readings:
        return AnalyticsResult("Health Score", None, datetime.now().timestamp(), 0)
    
    # Factors: signal strength, issues, response time
    scores = []
    for r in readings:
        score = 100
        # Deduct for weak signal
        if r.signal_strength < 50:
            score -= (50 - r.signal_strength)
        # Deduct for issues
        if r.issue != "none":
            score -= 20
        # Deduct for slow response
        if r.response_time_ms > 500:
            score -= min(30, (r.response_time_ms - 500) // 100)
        scores.append(max(0, score))
    
    avg = sum(scores) / len(scores)
    return AnalyticsResult(
        "Health Score",
        f"{round(avg, 1)}/100",
        datetime.now().timestamp(),
        len(readings)
    )


class AnalyticsPipeline:
    def __init__(self, readings):
        self._data = list(readings)
    
    @classmethod
    def from_raw(cls, updates):
        return cls([make_reading(u) for u in updates])
    
    def filter_type(self, dtype):
        filtered = [r for r in self._data if r.device_type == dtype]
        return AnalyticsPipeline(filtered)
    
    def filter_critical(self):
        return AnalyticsPipeline(get_critical(self._data))
    
    def get_readings(self):
        return self._data
    
    def calc_metrics(self):
        return {
            "average_temperature": avg_temp(self._data),
            "total_energy": total_energy(self._data),
            "average_battery": avg_battery(self._data),
            "active_devices": count_devices(self._data),
            "average_signal": avg_signal(self._data),
            "response_time": avg_response_time(self._data),
            "health_score": device_health_score(self._data)
        }
    
    def get_issue_breakdown(self):
        return issue_breakdown(self._data)
    
    def filter_issues(self):
        """Filter readings that have issues"""
        filtered = [r for r in self._data if r.issue != "none"]
        return AnalyticsPipeline(filtered)


def process_updates(raw_updates):
    pipe = AnalyticsPipeline.from_raw(raw_updates)
    return {
        "metrics": pipe.calc_metrics(),
        "critical_events": pipe.filter_critical().get_readings(),
        "total_readings": len(raw_updates),
        "issue_breakdown": pipe.get_issue_breakdown(),
        "issues_count": len(pipe.filter_issues().get_readings())
    }
