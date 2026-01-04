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


def f_make_reading(v_raw):
    """raw dict -> DeviceReading"""
    return DeviceReading(
        device_id=v_raw.get("device_id", "unknown"),
        device_type=v_raw.get("type", "GENERIC"),
        timestamp=v_raw.get("timestamp") or datetime.now().timestamp(),
        value=v_raw.get("payload", {}),
        signal_strength=v_raw.get("signal_strength", 100),
        status=v_raw.get("status", "online"),
        issue=v_raw.get("issue", "none"),
        response_time_ms=v_raw.get("response_time_ms", 50)
    )


def f_is_high_temp(v_r, v_thresh=30.0):
    if v_r.device_type != "THERMOSTAT":
        return False
    return v_r.value.get("current_temp", 0) > v_thresh

def f_is_low_batt(v_r, v_thresh=10.0):
    if v_r.device_type != "CAMERA":
        return False
    return v_r.value.get("battery_level", 100) < v_thresh

def f_has_motion(v_r):
    return v_r.device_type == "CAMERA" and v_r.value.get("motion_detected", False)

def f_has_issue(v_r):
    """Check if reading has any issue"""
    return v_r.issue != "none"


def f_get_critical(v_readings):
    """Filter for critical events using functional filter"""
    return list(filter(
        lambda r: f_is_high_temp(r) or f_is_low_batt(r) or f_has_motion(r),
        v_readings
    ))


def f_avg_temp(v_readings):
    """Calculate average temperature using functools.reduce"""
    v_thermos = list(filter(lambda r: r.device_type == "THERMOSTAT", v_readings))
    if not v_thermos:
        return AnalyticsResult("Average Temperature", None, datetime.now().timestamp(), 0)
    
    v_total_temp = reduce(
        lambda acc, r: acc + r.value.get("current_temp", 0),
        v_thermos,
        0
    )
    
    return AnalyticsResult(
        "Average Temperature",
        round(v_total_temp / len(v_thermos), 2),
        datetime.now().timestamp(),
        len(v_thermos)
    )


def f_total_energy(v_readings):
    """Calculate total energy consumption using functools.reduce"""
    v_on_bulbs = list(filter(
        lambda r: r.device_type == "BULB" and r.value.get("is_on"),
        v_readings
    ))
    
    if len(v_on_bulbs) == 0:
        return AnalyticsResult("Total Energy Consumption", 0.0, datetime.now().timestamp(), 0)
    
    v_total_watts = reduce(
        lambda acc, b: acc + (b.value.get("brightness", 0) / 100) * 10,
        v_on_bulbs,
        0
    )
    
    return AnalyticsResult(
        "Total Energy Consumption",
        round(v_total_watts, 2),
        datetime.now().timestamp(),
        len(v_on_bulbs)
    )


def f_avg_battery(v_readings):
    """Calculate average battery level using functools.reduce"""
    v_cams = list(filter(lambda r: r.device_type == "CAMERA", v_readings))
    if not v_cams:
        return AnalyticsResult("Average Battery Level", None, datetime.now().timestamp(), 0)
    
    v_total_battery = reduce(
        lambda acc, c: acc + c.value.get("battery_level", 0),
        v_cams,
        0
    )
    
    return AnalyticsResult(
        "Average Battery Level",
        round(v_total_battery / len(v_cams), 2),
        datetime.now().timestamp(),
        len(v_cams)
    )


def f_count_devices(v_readings):
    """Count unique active devices using functional map"""
    v_unique_ids = set(map(lambda r: r.device_id, v_readings))
    v_n = len(v_unique_ids)
    return AnalyticsResult("Active Devices", v_n, datetime.now().timestamp(), v_n)


def f_avg_signal(v_readings):
    """Calculate average signal strength across all devices"""
    if not v_readings:
        return AnalyticsResult("Average Signal Strength", None, datetime.now().timestamp(), 0)
    
    v_total = sum(r.signal_strength for r in v_readings)
    return AnalyticsResult(
        "Average Signal Strength",
        round(v_total / len(v_readings), 1),
        datetime.now().timestamp(),
        len(v_readings)
    )


def f_avg_response_time(v_readings):
    """Calculate average response time"""
    if not v_readings:
        return AnalyticsResult("Average Response Time", None, datetime.now().timestamp(), 0)
    
    v_total = sum(r.response_time_ms for r in v_readings)
    return AnalyticsResult(
        "Average Response Time",
        f"{round(v_total / len(v_readings), 1)}ms",
        datetime.now().timestamp(),
        len(v_readings)
    )


def f_issue_breakdown(v_readings):
    """Get breakdown of issues by type"""
    v_issues = defaultdict(int)
    for v_r in v_readings:
        if v_r.issue != "none":
            v_issues[v_r.issue] += 1
    return dict(v_issues)


def f_device_health_score(v_readings):
    """Calculate overall health score (0-100)"""
    if not v_readings:
        return AnalyticsResult("Health Score", None, datetime.now().timestamp(), 0)
    
    v_scores = []
    for v_r in v_readings:
        v_score = 100
        if v_r.signal_strength < 50:
            v_score -= (50 - v_r.signal_strength)
        if v_r.issue != "none":
            v_score -= 20
        if v_r.response_time_ms > 500:
            v_score -= min(30, (v_r.response_time_ms - 500) // 100)
        v_scores.append(max(0, v_score))
    
    v_avg = sum(v_scores) / len(v_scores)
    return AnalyticsResult(
        "Health Score",
        f"{round(v_avg, 1)}/100",
        datetime.now().timestamp(),
        len(v_readings)
    )


class AnalyticsPipeline:
    def __init__(self, v_readings):
        self._data = list(v_readings)
    
    @classmethod
    def from_raw(cls, v_updates):
        return cls([f_make_reading(u) for u in v_updates])
    
    def filter_type(self, v_dtype):
        v_filtered = [r for r in self._data if r.device_type == v_dtype]
        return AnalyticsPipeline(v_filtered)
    
    def filter_critical(self):
        return AnalyticsPipeline(f_get_critical(self._data))
    
    def get_readings(self):
        return self._data
    
    def calc_metrics(self):
        return {
            "average_temperature": f_avg_temp(self._data),
            "total_energy": f_total_energy(self._data),
            "average_battery": f_avg_battery(self._data),
            "active_devices": f_count_devices(self._data),
            "average_signal": f_avg_signal(self._data),
            "response_time": f_avg_response_time(self._data),
            "health_score": f_device_health_score(self._data)
        }
    
    def get_issue_breakdown(self):
        return f_issue_breakdown(self._data)
    
    def filter_issues(self):
        """Filter readings that have issues"""
        v_filtered = [r for r in self._data if r.issue != "none"]
        return AnalyticsPipeline(v_filtered)


def f_process_updates(v_raw_updates):
    v_pipe = AnalyticsPipeline.from_raw(v_raw_updates)
    return {
        "metrics": v_pipe.calc_metrics(),
        "critical_events": v_pipe.filter_critical().get_readings(),
        "total_readings": len(v_raw_updates),
        "issue_breakdown": v_pipe.get_issue_breakdown(),
        "issues_count": len(v_pipe.filter_issues().get_readings())
    }


# Keep old name for backwards compatibility
is_high_temp = f_is_high_temp
is_low_batt = f_is_low_batt
has_motion = f_has_motion
process_updates = f_process_updates
