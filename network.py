"""async network stuff"""

import argparse
import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from devices import SmartDevice, DeviceIssue, DeviceStatus
from storage import StorageWorker
from analytics import AnalyticsPipeline, is_high_temp, is_low_batt, has_motion


# Issue descriptions and actions
ISSUE_INFO = {
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
    
    def record_issue(self, device_id, issue: DeviceIssue):
        self.issues_detected[issue] += 1
        self.active_issues[device_id] = issue
    
    def record_resolution(self, device_id, issue: DeviceIssue):
        self.issues_resolved[issue] += 1
        if device_id in self.active_issues:
            del self.active_issues[device_id]
    
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
    _running: bool = field(default=False, init=False)
    _tasks: list = field(default_factory=list, init=False)
    _callbacks: list = field(default_factory=list, init=False)
    _readings: list = field(default_factory=list, init=False)
    _issue_tracker: IssueTracker = field(default_factory=IssueTracker, init=False)
    _update_count: int = field(default=0, init=False)
    
    def add_device(self, dev):
        self.devices.append(dev)
    
    def remove_device(self, did):
        for i, d in enumerate(self.devices):
            if d.device_id == did:
                del self.devices[i]
                return True
        return False
    
    def on_update(self, cb):
        self._callbacks.append(cb)
    
    async def connect_all(self):
        print("\nConnecting devices...")
        async with asyncio.TaskGroup() as tg:
            for d in self.devices:
                tg.create_task(d.connect())
        print("All devices connected!\n")
    
    async def _handle_issue(self, device, issue: DeviceIssue, reading: dict):
        """Handle a specific device issue with automatic fix attempt"""
        if issue not in ISSUE_INFO:
            return
        
        name, action = ISSUE_INFO[issue]
        payload = reading.get("payload", {})
        
        # Build context info
        context = ""
        result = None
        
        if issue == DeviceIssue.HIGH_TEMP:
            temp = payload.get("current_temp", 0)
            context = f"{temp:.1f}C"
            result = device.execute_command("cool")
            
        elif issue == DeviceIssue.LOW_TEMP:
            temp = payload.get("current_temp", 0)
            context = f"{temp:.1f}C"
            result = device.execute_command("heat")
            
        elif issue == DeviceIssue.HIGH_HUMIDITY:
            humidity = payload.get("humidity", 0)
            context = f"{humidity:.1f}%"
            result = device.execute_command("dehumidify")
            
        elif issue == DeviceIssue.SENSOR_MALFUNCTION:
            drift = payload.get("sensor_drift", 0)
            context = f"drift {drift:.1f}C"
            result = device.execute_command("calibrate")
            
        elif issue == DeviceIssue.LOW_BATTERY:
            battery = payload.get("battery_level", 0)
            context = f"{battery:.1f}%"
            # Just warn, don't auto-charge
            
        elif issue == DeviceIssue.CRITICAL_BATTERY:
            battery = payload.get("battery_level", 0)
            context = f"{battery:.1f}%"
            result = device.execute_command("charge")
            
        elif issue == DeviceIssue.STORAGE_FULL:
            storage = payload.get("storage_percent", 0)
            context = f"{storage:.1f}%"
            result = device.execute_command("clear_storage")
            
        elif issue == DeviceIssue.CONNECTION_LOST:
            context = "signal lost"
            await device.reconnect()
            result = f"reconnected ({device.signal_strength}%)"
            
        elif issue == DeviceIssue.WEAK_SIGNAL:
            signal = reading.get("signal_strength", 0)
            context = f"{signal}%"
            new_signal = device.boost_signal()
            result = f"boosted to {new_signal}%"
            
        elif issue == DeviceIssue.FIRMWARE_UPDATE:
            context = f"v{device._firmware_version}"
            device.update_firmware()
            result = f"updated to v{device._firmware_version}"
            
        elif issue == DeviceIssue.BULB_FLICKERING:
            brightness = payload.get("brightness", 0)
            context = f"{brightness}% brightness"
            result = device.execute_command("fix_flicker")
            
        elif issue == DeviceIssue.OVERLOAD:
            power = payload.get("power_draw", 0)
            context = f"{power:.1f}W"
            result = device.execute_command("reduce_load")
            
        elif issue == DeviceIssue.UNRESPONSIVE:
            response_time = reading.get("response_time_ms", 0)
            context = f"{response_time}ms latency"
            await device.reconnect()
            result = "restarted"
            
        elif issue == DeviceIssue.MOTION_ALERT:
            print(f"  [MOTION] {device.name} @ {device.location}")
            return
        
        # Print issue and resolution
        print(f"  [{name.upper()}] {device.name} ({context})")
        if result:
            print(f"    -> {action}: {result}")
            self._issue_tracker.record_resolution(device.device_id, issue)
        
        await asyncio.sleep(0.3)
    
    async def _update_loop(self, dev):
        while self._running:
            wait = random.uniform(self.update_interval[0], self.update_interval[1])
            await asyncio.sleep(wait)
            
            if not self._running:
                break
            
            upd = await dev.send_update()
            if upd:
                self._update_count += 1
                self._readings.append(upd)
                if self.storage:
                    self.storage.enqueue(upd)
                for c in self._callbacks:
                    c(upd)
    
    async def _check_loop(self, interval=2.0):
        """Monitor for issues and handle them"""
        handled_recently = {}
        cooldown = 5.0
        
        while self._running:
            await asyncio.sleep(interval)
            if not self._running or len(self._readings) == 0:
                continue
            
            recent_readings = self._readings[-len(self.devices)*2:]
            
            for reading in recent_readings:
                device_id = reading.get("device_id")
                issue_str = reading.get("issue", "none")
                
                if issue_str == "none":
                    continue
                
                now = asyncio.get_event_loop().time()
                if device_id in handled_recently:
                    if now - handled_recently[device_id] < cooldown:
                        continue
                
                device = None
                for d in self.devices:
                    if d.device_id == device_id:
                        device = d
                        break
                
                if not device:
                    continue
                
                try:
                    issue = DeviceIssue(issue_str)
                except ValueError:
                    continue
                
                if issue != DeviceIssue.MOTION_ALERT:
                    handled_recently[device_id] = now
                    self._issue_tracker.record_issue(device_id, issue)
                
                await self._handle_issue(device, issue, reading)
    
    async def start(self, duration=None):
        self._running = True
        
        for d in self.devices:
            if d.is_connected:
                self._tasks.append(asyncio.create_task(self._update_loop(d)))
        
        self._tasks.append(asyncio.create_task(self._check_loop()))
        
        if duration:
            await asyncio.sleep(duration)
            await self.stop()
        else:
            try:
                await asyncio.gather(*self._tasks)
            except asyncio.CancelledError:
                pass
    
    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
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


async def run_demo(devices, storage, secs=30):
    ctrl = NetworkController(devices=devices, storage=storage)
    await ctrl.connect_all()
    print(f"Running for {secs}s...")
    await ctrl.start(duration=secs)
    print(f"\nGot {len(ctrl.get_readings())} updates")


class DeviceSimulator:
    """test helper"""
    def __init__(self, ctrl):
        self.ctrl = ctrl
    
    async def temp_spike(self, did, target=35, secs=5):
        for d in self.ctrl.devices:
            if d.device_id == did and d.device_type == "THERMOSTAT":
                old = d.current_temp
                d.current_temp = target
                await asyncio.sleep(secs)
                d.current_temp = old
                return
    
    async def trigger_motion(self, did, secs=2):
        for d in self.ctrl.devices:
            if d.device_id == did and d.device_type == "CAMERA":
                d.motion_detected = True
                await asyncio.sleep(secs)
                d.motion_detected = False
                return
    
    async def drain_battery(self, did, rate=1, secs=60):
        for d in self.ctrl.devices:
            if d.device_id == did and d.device_type == "CAMERA":
                end = asyncio.get_event_loop().time() + secs
                while asyncio.get_event_loop().time() < end:
                    d.battery_level -= rate
                    if d.battery_level <= 0:
                        return
                    await asyncio.sleep(1)
                return


def parse_args():
    parser = argparse.ArgumentParser(description="Smart device network monitor")
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=30,
        help="Duration in seconds to run the monitor (default: 30)"
    )
    return parser.parse_args()


async def main():
    """Demo entry point - use main.py for full functionality"""
    from devices import SmartBulb, SmartThermostat, SmartCamera
    
    args = parse_args()
    
    # Create sample devices using concrete classes (not abstract SmartDevice)
    devices = [
        SmartThermostat("thermo-001", "Living Room Thermostat", "Living Room"),
        SmartCamera("cam-001", "Front Door Camera", "Front Door"),
        SmartBulb("light-001", "Kitchen Light", "Kitchen"),
        SmartThermostat("thermo-002", "Bedroom Thermostat", "Bedroom"),
        SmartCamera("cam-002", "Backyard Camera", "Backyard"),
    ]
    
    storage = StorageWorker()
    storage.start()
    
    try:
        await run_demo(devices, storage, secs=args.duration)
    finally:
        storage.stop()


if __name__ == "__main__":
    asyncio.run(main())
