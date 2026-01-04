"""async network stuff"""

import argparse
import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from devices import SmartDevice, DeviceIssue, DeviceStatus
from storage import StorageWorker
from analytics import AnalyticsPipeline, f_is_high_temp, f_is_low_batt, f_has_motion


C_ISSUE_INFO = {
    DeviceIssue.HIGH_TEMP: ("High Temperature", "Activating cooling"),
    DeviceIssue.LOW_TEMP: ("Low Temperature", "Activating heating"),
    DeviceIssue.HIGH_HUMIDITY: ("High Humidity", "Running dehumidifier"),
    DeviceIssue.LOW_BATTERY: ("Low Battery", "Warning"),
    DeviceIssue.CRITICAL_BATTERY: ("Critical Battery", "Starting charge"),
    DeviceIssue.CONNECTION_LOST: ("Connection Lost", "Reconnecting"),
    DeviceIssue.WEAK_SIGNAL: ("Weak Signal", "Boosting signal"),
    DeviceIssue.FIRMWARE_UPDATE: ("Firmware Update", "Installing update"),
    DeviceIssue.SENSOR_MALFUNCTION: ("Sensor Drift", "Recalibrating"),
    DeviceIssue.STORAGE_FULL: ("Storage Full", "Clearing old files"),
    DeviceIssue.MOTION_ALERT: ("Motion Detected", "Recording"),
    DeviceIssue.BULB_FLICKERING: ("Bulb Flickering", "Resetting bulb"),
    DeviceIssue.UNRESPONSIVE: ("Unresponsive", "Restarting device"),
    DeviceIssue.OVERLOAD: ("Overload Warning", "Reducing load"),
}


@dataclass
class IssueTracker:
    """Track issues and their resolutions"""
    issues_detected: dict = field(default_factory=lambda: defaultdict(int))
    issues_resolved: dict = field(default_factory=lambda: defaultdict(int))
    active_issues: dict = field(default_factory=dict)
    
    def record_issue(self, v_device_id, v_issue: DeviceIssue):
        self.issues_detected[v_issue] += 1
        self.active_issues[v_device_id] = v_issue
    
    def record_resolution(self, v_device_id, v_issue: DeviceIssue):
        self.issues_resolved[v_issue] += 1
        if v_device_id in self.active_issues:
            del self.active_issues[v_device_id]
    
    def get_summary(self):
        return {
            "detected": dict(self.issues_detected),
            "resolved": dict(self.issues_resolved),
            "active": len(self.active_issues)
        }


@dataclass
class NetworkController:
    devices: list = field(default_factory=list)
    storage: StorageWorker = None
    update_interval: tuple = (1.0, 3.0)
    speed: float = 1.0
    _running: bool = field(default=False, init=False)
    _tasks: list = field(default_factory=list, init=False)
    _callbacks: list = field(default_factory=list, init=False)
    _readings: list = field(default_factory=list, init=False)
    _issue_tracker: IssueTracker = field(default_factory=IssueTracker, init=False)
    _update_count: int = field(default=0, init=False)
    
    def add_device(self, v_dev):
        self.devices.append(v_dev)
    
    def remove_device(self, v_did):
        for v_i, v_d in enumerate(self.devices):
            if v_d.device_id == v_did:
                del self.devices[v_i]
                return True
        return False
    
    def on_update(self, v_cb):
        self._callbacks.append(v_cb)
    
    async def connect_all(self):
        print("\nConnecting devices...")
        async with asyncio.TaskGroup() as tg:
            for v_d in self.devices:
                tg.create_task(v_d.connect())
        print("All devices connected!\n")
    
    async def _handle_issue(self, v_device, v_issue: DeviceIssue, v_reading: dict):
        """Handle a specific device issue with automatic fix attempt"""
        if v_issue not in C_ISSUE_INFO:
            return
        
        v_name, v_action = C_ISSUE_INFO[v_issue]
        v_payload = v_reading.get("payload", {})
        
        v_context = ""
        v_result = None
        
        if v_issue == DeviceIssue.HIGH_TEMP:
            v_temp = v_payload.get("current_temp", 0)
            v_context = f"{v_temp:.1f}C"
            v_result = v_device.execute_command("cool")
            
        elif v_issue == DeviceIssue.LOW_TEMP:
            v_temp = v_payload.get("current_temp", 0)
            v_context = f"{v_temp:.1f}C"
            v_result = v_device.execute_command("heat")
            
        elif v_issue == DeviceIssue.HIGH_HUMIDITY:
            v_humidity = v_payload.get("humidity", 0)
            v_context = f"{v_humidity:.1f}%"
            v_result = v_device.execute_command("dehumidify")
            
        elif v_issue == DeviceIssue.SENSOR_MALFUNCTION:
            v_drift = v_payload.get("sensor_drift", 0)
            v_context = f"drift {v_drift:.1f}C"
            v_result = v_device.execute_command("calibrate")
            
        elif v_issue == DeviceIssue.LOW_BATTERY:
            v_battery = v_payload.get("battery_level", 0)
            v_context = f"{v_battery:.1f}%"
            
        elif v_issue == DeviceIssue.CRITICAL_BATTERY:
            v_battery = v_payload.get("battery_level", 0)
            v_context = f"{v_battery:.1f}%"
            v_result = v_device.execute_command("charge")
            
        elif v_issue == DeviceIssue.STORAGE_FULL:
            v_storage = v_payload.get("storage_percent", 0)
            v_context = f"{v_storage:.1f}%"
            v_result = v_device.execute_command("clear_storage")
            
        elif v_issue == DeviceIssue.CONNECTION_LOST:
            v_context = "signal lost"
            await v_device.reconnect()
            v_result = f"reconnected ({v_device.signal_strength}%)"
            
        elif v_issue == DeviceIssue.WEAK_SIGNAL:
            v_signal = v_reading.get("signal_strength", 0)
            v_context = f"{v_signal}%"
            v_new_signal = v_device.boost_signal()
            v_result = f"boosted to {v_new_signal}%"
            
        elif v_issue == DeviceIssue.FIRMWARE_UPDATE:
            v_context = f"v{v_device._firmware_version}"
            v_device.update_firmware()
            v_result = f"updated to v{v_device._firmware_version}"
            
        elif v_issue == DeviceIssue.BULB_FLICKERING:
            v_brightness = v_payload.get("brightness", 0)
            v_context = f"{v_brightness}% brightness"
            v_result = v_device.execute_command("fix_flicker")
            
        elif v_issue == DeviceIssue.OVERLOAD:
            v_power = v_payload.get("power_draw", 0)
            v_context = f"{v_power:.1f}W"
            v_result = v_device.execute_command("reduce_load")
            
        elif v_issue == DeviceIssue.UNRESPONSIVE:
            v_response_time = v_reading.get("response_time_ms", 0)
            v_context = f"{v_response_time}ms latency"
            await v_device.reconnect()
            v_result = "restarted"
            
        elif v_issue == DeviceIssue.MOTION_ALERT:
            print(f"  [MOTION] {v_device.name} @ {v_device.location}")
            return
        
        print(f"  [{v_name.upper()}] {v_device.name} ({v_context})")
        if v_result:
            print(f"    -> {v_action}: {v_result}")
            self._issue_tracker.record_resolution(v_device.device_id, v_issue)
        
        await asyncio.sleep(0.3 / self.speed)
    
    async def _update_loop(self, v_dev):
        while self._running:
            v_wait = random.uniform(self.update_interval[0], self.update_interval[1]) / self.speed
            await asyncio.sleep(v_wait)
            
            if not self._running:
                break
            
            v_upd = await v_dev.send_update()
            if v_upd:
                self._update_count += 1
                self._readings.append(v_upd)
                if self.storage:
                    self.storage.enqueue(v_upd)
                for v_c in self._callbacks:
                    v_c(v_upd)
    
    async def _check_loop(self, v_interval=2.0):
        """Monitor for issues and handle them"""
        v_handled_recently = {}
        v_cooldown = 5.0
        
        while self._running:
            await asyncio.sleep(v_interval / self.speed)
            if not self._running or len(self._readings) == 0:
                continue
            
            v_recent_readings = self._readings[-len(self.devices)*2:]
            
            for v_reading in v_recent_readings:
                v_device_id = v_reading.get("device_id")
                v_issue_str = v_reading.get("issue", "none")
                
                if v_issue_str == "none":
                    continue
                
                v_now = asyncio.get_event_loop().time()
                if v_device_id in v_handled_recently:
                    if v_now - v_handled_recently[v_device_id] < v_cooldown:
                        continue
                
                v_device = None
                for v_d in self.devices:
                    if v_d.device_id == v_device_id:
                        v_device = v_d
                        break
                
                if not v_device:
                    continue
                
                try:
                    v_issue = DeviceIssue(v_issue_str)
                except ValueError:
                    continue
                
                if v_issue != DeviceIssue.MOTION_ALERT:
                    v_handled_recently[v_device_id] = v_now
                    self._issue_tracker.record_issue(v_device_id, v_issue)
                
                await self._handle_issue(v_device, v_issue, v_reading)
    
    async def start(self, v_duration=None):
        self._running = True
        
        for v_d in self.devices:
            if v_d.is_connected:
                self._tasks.append(asyncio.create_task(self._update_loop(v_d)))
        
        self._tasks.append(asyncio.create_task(self._check_loop()))
        
        if v_duration:
            await asyncio.sleep(v_duration)
            await self.stop()
        else:
            try:
                await asyncio.gather(*self._tasks)
            except asyncio.CancelledError:
                pass
    
    async def stop(self):
        self._running = False
        for v_t in self._tasks:
            v_t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        print(f"\nMonitoring stopped. ({self._update_count} updates)")
    
    def get_readings(self):
        return self._readings[:]
    
    def clear_readings(self):
        self._readings = []
    
    def get_issue_summary(self):
        return self._issue_tracker.get_summary()


async def f_run_demo(v_devices, v_storage, v_secs=30):
    v_ctrl = NetworkController(devices=v_devices, storage=v_storage)
    await v_ctrl.connect_all()
    print(f"Running for {v_secs}s...")
    await v_ctrl.start(v_duration=v_secs)
    print(f"\nGot {len(v_ctrl.get_readings())} updates")


class DeviceSimulator:
    """test helper"""
    def __init__(self, v_ctrl):
        self.ctrl = v_ctrl
    
    async def temp_spike(self, v_did, v_target=35, v_secs=5):
        for v_d in self.ctrl.devices:
            if v_d.device_id == v_did and v_d.device_type == "THERMOSTAT":
                v_old = v_d.current_temp
                v_d.current_temp = v_target
                await asyncio.sleep(v_secs)
                v_d.current_temp = v_old
                return
    
    async def trigger_motion(self, v_did, v_secs=2):
        for v_d in self.ctrl.devices:
            if v_d.device_id == v_did and v_d.device_type == "CAMERA":
                v_d.motion_detected = True
                await asyncio.sleep(v_secs)
                v_d.motion_detected = False
                return
    
    async def drain_battery(self, v_did, v_rate=1, v_secs=60):
        for v_d in self.ctrl.devices:
            if v_d.device_id == v_did and v_d.device_type == "CAMERA":
                v_end = asyncio.get_event_loop().time() + v_secs
                while asyncio.get_event_loop().time() < v_end:
                    v_d.battery_level -= v_rate
                    if v_d.battery_level <= 0:
                        return
                    await asyncio.sleep(1)
                return


def f_parse_args():
    v_parser = argparse.ArgumentParser(description="Smart device network monitor")
    v_parser.add_argument(
        "--runtime",
        type=int,
        default=30,
        help="Duration in seconds to run the monitor (default: 30)"
    )
    v_parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speed multiplier (default: 1.0)"
    )
    return v_parser.parse_args()


async def f_main():
    """Demo entry point - use main.py for full functionality"""
    from devices import SmartBulb, SmartThermostat, SmartCamera
    
    v_args = f_parse_args()
    
    v_devices = [
        SmartThermostat("thermo1", "Living Room Thermostat", "Living Room"),
        SmartCamera("seccam1", "Front Door Camera", "Front Door"),
        SmartBulb("bulb1", "Kitchen Light", "Kitchen"),
        SmartThermostat("thermo2", "Bedroom Thermostat", "Bedroom"),
        SmartCamera("seccam2", "Backyard Camera", "Backyard"),
    ]
    
    v_storage = StorageWorker()
    v_storage.start()
    
    try:
        await f_run_demo(v_devices, v_storage, v_secs=v_args.runtime)
    finally:
        v_storage.stop()


if __name__ == "__main__":
    asyncio.run(f_main())
