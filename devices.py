"""devices"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random
import asyncio


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"
    UPDATING = "updating"


class DeviceIssue(Enum):
    NONE = "none"
    HIGH_TEMP = "high_temp"
    LOW_TEMP = "low_temp"
    HIGH_HUMIDITY = "high_humidity"
    LOW_BATTERY = "low_battery"
    CRITICAL_BATTERY = "critical_battery"
    CONNECTION_LOST = "connection_lost"
    WEAK_SIGNAL = "weak_signal"
    FIRMWARE_UPDATE = "firmware_update"
    SENSOR_MALFUNCTION = "sensor_malfunction"
    STORAGE_FULL = "storage_full"
    MOTION_ALERT = "motion_alert"
    BULB_FLICKERING = "bulb_flickering"
    UNRESPONSIVE = "unresponsive"
    OVERLOAD = "overload"
    # Water-related issues
    LEAK_DETECTED = "leak_detected"
    HIGH_FLOW = "high_flow"
    ABNORMAL_USAGE = "abnormal_usage"


@dataclass
class SmartDevice(ABC):
    device_id: str
    name: str
    location: str
    device_type: str = field(default="GENERIC", init=False)
    _is_connected: bool = field(default=False, init=False, repr=False)
    _signal_strength: int = field(default=100, init=False, repr=False)
    _firmware_version: str = field(default="1.0.0", init=False, repr=False)
    _needs_update: bool = field(default=False, init=False, repr=False)
    _status: DeviceStatus = field(default=DeviceStatus.OFFLINE, init=False, repr=False)
    _current_issue: DeviceIssue = field(default=DeviceIssue.NONE, init=False, repr=False)
    _response_time_ms: int = field(default=50, init=False, repr=False)
    
    @property
    def is_connected(self):
        return self._is_connected
    
    @property
    def signal_strength(self):
        return self._signal_strength
    
    @signal_strength.setter
    def signal_strength(self, v):
        self._signal_strength = max(0, min(100, int(v)))
    
    @property
    def status(self):
        return self._status
    
    @property
    def current_issue(self):
        return self._current_issue
    
    async def connect(self):
        print(f"{self.name} is connecting...")
        delay = random.uniform(0.5, 2.0)
        await asyncio.sleep(delay)
        self._is_connected = True
        self._status = DeviceStatus.ONLINE
        self._signal_strength = random.randint(60, 100)
        self._needs_update = random.random() < 0.15  # 15% chance needs update
        print(f"{self.name} connected successfully in {delay:.2f}s.")
    
    def disconnect(self):
        self._is_connected = False
        self._status = DeviceStatus.OFFLINE
        print(f"{self.name} disconnected.")
    
    async def reconnect(self):
        """Attempt to reconnect the device"""
        self._is_connected = False
        self._status = DeviceStatus.OFFLINE
        await asyncio.sleep(random.uniform(0.5, 1.5))
        self._is_connected = True
        self._status = DeviceStatus.ONLINE
        self._signal_strength = random.randint(70, 100)
        self._current_issue = DeviceIssue.NONE
        return True
    
    def update_firmware(self):
        """Simulate firmware update"""
        self._firmware_version = "1.1.0"
        self._needs_update = False
        self._current_issue = DeviceIssue.NONE
        return True
    
    def boost_signal(self):
        """Boost signal strength (simulates moving closer to router or signal optimization)"""
        self._signal_strength = min(100, self._signal_strength + 40)
        self._current_issue = DeviceIssue.NONE
        self._status = DeviceStatus.ONLINE
        return self._signal_strength
    
    def _simulate_issues(self):
        """Randomly introduce device issues"""
        # Signal fluctuation - realistic wireless behavior
        # Signal can go up or down slightly, with occasional dips
        if random.random() < 0.15:
            # 15% chance of signal change
            change = random.randint(-8, 5)  # Slightly biased toward decrease
            self._signal_strength += change
            self._signal_strength = max(20, min(100, self._signal_strength))
        
        # Occasional signal recovery (simulates network optimization)
        if self._signal_strength < 60 and random.random() < 0.1:
            self._signal_strength += random.randint(5, 15)
            self._signal_strength = min(100, self._signal_strength)
        
        # Connection drops (very rare, only when signal is critically low)
        if random.random() < 0.01 and self._signal_strength < 25:
            self._is_connected = False
            self._status = DeviceStatus.OFFLINE
            self._current_issue = DeviceIssue.CONNECTION_LOST
            return DeviceIssue.CONNECTION_LOST
        
        # Weak signal warning (only when significantly low)
        if self._signal_strength < 30:
            self._current_issue = DeviceIssue.WEAK_SIGNAL
            self._status = DeviceStatus.WARNING
            return DeviceIssue.WEAK_SIGNAL
        
        # Firmware update needed (rare)
        if self._needs_update and random.random() < 0.02:
            self._current_issue = DeviceIssue.FIRMWARE_UPDATE
            self._status = DeviceStatus.WARNING
            return DeviceIssue.FIRMWARE_UPDATE
        
        # Unresponsive (high response time) - rare
        if random.random() < 0.01:
            self._response_time_ms = random.randint(2000, 5000)
            self._current_issue = DeviceIssue.UNRESPONSIVE
            self._status = DeviceStatus.ERROR
            return DeviceIssue.UNRESPONSIVE
        
        # Normal operation - clear any previous issues
        if self._current_issue in [DeviceIssue.WEAK_SIGNAL, DeviceIssue.UNRESPONSIVE]:
            self._current_issue = DeviceIssue.NONE
            self._status = DeviceStatus.ONLINE
        
        self._response_time_ms = random.randint(20, 150)
        return None
    
    async def send_update(self):
        if self._is_connected == False:
            return None
        
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        base_issue = self._simulate_issues()
        device_issue = self._get_device_specific_issue()
        
        return {
            "device_id": self.device_id,
            "type": self.device_type,
            "timestamp": datetime.now().timestamp(),
            "payload": self._get_payload(),
            "signal_strength": self._signal_strength,
            "status": self._status.value,
            "issue": (device_issue or base_issue or DeviceIssue.NONE).value,
            "response_time_ms": self._response_time_ms
        }
    
    @abstractmethod
    def _get_payload(self):
        pass
    
    @abstractmethod
    def _get_device_specific_issue(self):
        """Return device-specific issue or None"""
        pass
    
    @abstractmethod
    def execute_command(self, command, **kwargs):
        pass


@dataclass
class SmartBulb(SmartDevice):
    _is_on: bool = field(default=False, init=False)
    _brightness: int = field(default=100, init=False)
    _power_draw: float = field(default=0.0, init=False)
    _is_flickering: bool = field(default=False, init=False)
    _color_temp: int = field(default=4000, init=False)  # Kelvin
    
    def __post_init__(self):
        self.device_type = "BULB"
    
    @property
    def is_on(self):
        return self._is_on
    
    @is_on.setter
    def is_on(self, value):
        self._is_on = bool(value)
    
    @property
    def brightness(self):
        return self._brightness
    
    @brightness.setter
    def brightness(self, value):
        v = int(value)
        if v < 0: v = 0
        if v > 100: v = 100
        self._brightness = v
    
    def _get_payload(self):
        # Calculate power draw
        if self._is_on:
            self._power_draw = (self._brightness / 100) * 10  # 10W max
        else:
            self._power_draw = 0.1  # standby
        
        return {
            "is_on": self._is_on, 
            "brightness": self._brightness,
            "power_draw": self._power_draw,
            "color_temp": self._color_temp,
            "flickering": self._is_flickering
        }
    
    def _get_device_specific_issue(self):
        # Flickering issue (more likely when brightness is high or power fluctuates)
        if self._is_on and random.random() < 0.04:
            self._is_flickering = True
            self._current_issue = DeviceIssue.BULB_FLICKERING
            self._status = DeviceStatus.WARNING
            return DeviceIssue.BULB_FLICKERING
        
        # Overload when at max brightness for too long
        if self._is_on and self._brightness == 100 and random.random() < 0.02:
            self._current_issue = DeviceIssue.OVERLOAD
            self._status = DeviceStatus.WARNING
            return DeviceIssue.OVERLOAD
        
        self._is_flickering = False
        return None
    
    def fix_flicker(self):
        """Reset the bulb to fix flickering"""
        self._is_flickering = False
        self._brightness = max(80, self._brightness - 10)  # Reduce brightness slightly
        self._current_issue = DeviceIssue.NONE
        self._status = DeviceStatus.ONLINE
        return True
    
    def reduce_load(self):
        """Reduce brightness to prevent overload"""
        self._brightness = min(75, self._brightness)
        self._current_issue = DeviceIssue.NONE
        self._status = DeviceStatus.ONLINE
        return self._brightness
    
    def execute_command(self, command, **kwargs):
        if command == "turn_on":
            self._is_on = True
            return "ok"
        if command == "turn_off":
            self._is_on = False
            return "ok"
        if command == "set_brightness":
            self.brightness = kwargs.get("level", 100)
            return f"brightness={self._brightness}"
        if command == "toggle":
            self._is_on = not self._is_on
            return "toggled"
        if command == "fix_flicker":
            return "fixed" if self.fix_flicker() else "failed"
        if command == "reduce_load":
            return f"reduced to {self.reduce_load()}%"
        return "?"


# thermostat is more involved
class SmartThermostat(SmartDevice):
    def __init__(self, device_id, name, location):
        self.device_id = device_id
        self.name = name
        self.location = location
        self.device_type = "THERMOSTAT"
        self._is_connected = False
        self._current_temp = 22.0
        self._target_temp = 24.0
        self._humidity = 50.0
        self._hvac_mode = "auto"  # auto, heat, cool, off
        self._sensor_drift = 0.0
        self._calibration_needed = False
        self._signal_strength = 100
        self._needs_update = False
        self._status = DeviceStatus.OFFLINE
        self._current_issue = DeviceIssue.NONE
        self._response_time_ms = 50
    
    @property
    def current_temp(self):
        return self._current_temp
    
    @current_temp.setter
    def current_temp(self, v):
        self._current_temp = float(v)
    
    @property
    def target_temp(self):
        return self._target_temp
    
    @target_temp.setter
    def target_temp(self, v):
        v = float(v)
        # dont let ppl set crazy temps
        if v < -10: v = -10
        if v > 50: v = 50
        self._target_temp = v
    
    @property
    def humidity(self):
        return self._humidity
    
    @humidity.setter
    def humidity(self, v):
        v = float(v)
        if v < 0: v = 0
        if v > 100: v = 100
        self._humidity = v
    
    def _get_payload(self):
        # wiggle the values a bit to simulate real sensor
        self._current_temp += random.uniform(-2, 2)
        self._humidity += random.uniform(-5, 5)
        if self._humidity < 0: self._humidity = 0
        if self._humidity > 100: self._humidity = 100
        
        # Add sensor drift over time
        if random.random() < 0.03:
            self._sensor_drift += random.uniform(-0.5, 0.5)
        
        return {
            "current_temp": self._current_temp + self._sensor_drift,
            "target_temp": self._target_temp,
            "humidity": self._humidity,
            "hvac_mode": self._hvac_mode,
            "sensor_drift": abs(self._sensor_drift)
        }
    
    def _get_device_specific_issue(self):
        reported_temp = self._current_temp + self._sensor_drift
        
        # High temperature
        if reported_temp > 30:
            self._current_issue = DeviceIssue.HIGH_TEMP
            self._status = DeviceStatus.WARNING
            return DeviceIssue.HIGH_TEMP
        
        # Low temperature
        if reported_temp < 15:
            self._current_issue = DeviceIssue.LOW_TEMP
            self._status = DeviceStatus.WARNING
            return DeviceIssue.LOW_TEMP
        
        # High humidity (mold risk)
        if self._humidity > 75:
            self._current_issue = DeviceIssue.HIGH_HUMIDITY
            self._status = DeviceStatus.WARNING
            return DeviceIssue.HIGH_HUMIDITY
        
        # Sensor malfunction (too much drift)
        if abs(self._sensor_drift) > 3:
            self._calibration_needed = True
            self._current_issue = DeviceIssue.SENSOR_MALFUNCTION
            self._status = DeviceStatus.ERROR
            return DeviceIssue.SENSOR_MALFUNCTION
        
        return None
    
    def calibrate_sensor(self):
        """Recalibrate the temperature sensor"""
        self._sensor_drift = 0.0
        self._calibration_needed = False
        self._current_issue = DeviceIssue.NONE
        self._status = DeviceStatus.ONLINE
        return True
    
    def activate_dehumidifier(self):
        """Turn on dehumidifier mode"""
        self._humidity = max(40, self._humidity - 15)
        if self._humidity <= 75:
            self._current_issue = DeviceIssue.NONE
            self._status = DeviceStatus.ONLINE
        return self._humidity
    
    def execute_command(self, command, **kwargs):
        if command == "set_target":
            self.target_temp = kwargs.get("temp", 24)
            return f"target={self._target_temp}"
        elif command == "cool":
            self._current_temp -= 2
            self._hvac_mode = "cool"
            return "cooling"
        elif command == "heat":
            self._current_temp += 2
            self._hvac_mode = "heat"
            return "heating"
        elif command == "calibrate":
            return "calibrated" if self.calibrate_sensor() else "failed"
        elif command == "dehumidify":
            return f"humidity now {self.activate_dehumidifier()}%"
        return "unknown cmd"


@dataclass
class SmartCamera(SmartDevice):
    _motion_detected: bool = field(default=False, init=False)
    _battery_level: float = field(default=100.0, init=False)
    _last_snapshot: float = field(default=0.0, init=False)
    _storage_used_mb: float = field(default=0.0, init=False)
    _storage_capacity_mb: float = field(default=32000.0, init=False)  # 32GB
    _night_vision: bool = field(default=True, init=False)
    _recording: bool = field(default=False, init=False)
    _is_charging: bool = field(default=False, init=False)
    
    def __post_init__(self):
        self.device_type = "CAMERA"
        self._last_snapshot = datetime.now().timestamp()
        self._storage_used_mb = random.uniform(5000, 20000)  # Start with some storage used
    
    @property
    def motion_detected(self):
        return self._motion_detected
    
    @motion_detected.setter
    def motion_detected(self, v):
        self._motion_detected = bool(v)
    
    @property
    def battery_level(self):
        return self._battery_level
    
    @battery_level.setter
    def battery_level(self, v):
        self._battery_level = max(0, min(100, float(v)))
    
    @property
    def last_snapshot(self):
        return self._last_snapshot
    
    @property
    def storage_percent(self):
        return (self._storage_used_mb / self._storage_capacity_mb) * 100
    
    def take_snapshot(self):
        self._last_snapshot = datetime.now().timestamp()
        self._battery_level -= 0.5
        self._storage_used_mb += random.uniform(1, 5)  # Each snapshot uses storage
        if self._battery_level < 0:
            self._battery_level = 0
    
    def _get_payload(self):
        # random motion check
        self._motion_detected = random.random() < 0.3
        # drain battery (slower if charging)
        if self._is_charging:
            self._battery_level += random.uniform(0.5, 1.0)
            self._battery_level = min(100, self._battery_level)
        else:
            self._battery_level -= random.uniform(0.1, 0.5)
        if self._battery_level < 0:
            self._battery_level = 0
        if self._motion_detected:
            self.take_snapshot()
            self._recording = True
            self._storage_used_mb += random.uniform(10, 50)  # Recording uses more storage
        else:
            self._recording = False
        
        return {
            "motion_detected": self._motion_detected,
            "last_snapshot": self._last_snapshot,
            "battery_level": self._battery_level,
            "storage_percent": round(self.storage_percent, 1),
            "night_vision": self._night_vision,
            "recording": self._recording,
            "charging": self._is_charging
        }
    
    def _get_device_specific_issue(self):
        # Critical battery
        if self._battery_level < 5:
            self._current_issue = DeviceIssue.CRITICAL_BATTERY
            self._status = DeviceStatus.ERROR
            return DeviceIssue.CRITICAL_BATTERY
        
        # Low battery
        if self._battery_level < 20:
            self._current_issue = DeviceIssue.LOW_BATTERY
            self._status = DeviceStatus.WARNING
            return DeviceIssue.LOW_BATTERY
        
        # Storage full
        if self.storage_percent > 90:
            self._current_issue = DeviceIssue.STORAGE_FULL
            self._status = DeviceStatus.WARNING
            return DeviceIssue.STORAGE_FULL
        
        # Motion alert (important but not an error)
        if self._motion_detected:
            self._current_issue = DeviceIssue.MOTION_ALERT
            return DeviceIssue.MOTION_ALERT
        
        return None
    
    def start_charging(self):
        """Start charging the battery"""
        self._is_charging = True
        self._current_issue = DeviceIssue.NONE
        self._status = DeviceStatus.ONLINE
        return True
    
    def clear_storage(self):
        """Delete old recordings to free up space"""
        self._storage_used_mb = self._storage_capacity_mb * 0.3  # Keep 30%
        if self.storage_percent <= 90:
            self._current_issue = DeviceIssue.NONE
            self._status = DeviceStatus.ONLINE
        return round(self.storage_percent, 1)
    
    def execute_command(self, command, **kwargs):
        if command == "snapshot":
            self.take_snapshot()
            return "snap"
        if command == "arm":
            return "armed"
        if command == "disarm":
            self._motion_detected = False
            return "disarmed"
        if command == "charge":
            return "charging" if self.start_charging() else "failed"
        if command == "clear_storage":
            return f"storage at {self.clear_storage()}%"
        return "?"


# ============================================================================
# Smart Water Meter - Tracks water consumption
# ============================================================================

@dataclass
class SmartWaterMeter(SmartDevice):
    """Smart water meter for tracking water consumption"""
    _flow_rate: float = field(default=0.0, init=False)  # liters per minute
    _total_usage_liters: float = field(default=0.0, init=False)
    _daily_usage_liters: float = field(default=0.0, init=False)
    _monthly_usage_liters: float = field(default=0.0, init=False)
    _is_flowing: bool = field(default=False, init=False)
    _leak_detected: bool = field(default=False, init=False)
    _valve_open: bool = field(default=True, init=False)
    _water_source: str = field(default="main", init=False)  # main, bathroom, kitchen, garden
    _pressure_bar: float = field(default=3.0, init=False)
    _temperature_c: float = field(default=18.0, init=False)  # Water temperature
    _last_usage_time: float = field(default=0.0, init=False)
    
    def __post_init__(self):
        self.device_type = "WATER_METER"
        self._last_usage_time = datetime.now().timestamp()
        # Initialize with some realistic monthly usage (average household ~150L/day per person)
        self._monthly_usage_liters = random.uniform(3000, 8000)
        self._daily_usage_liters = random.uniform(50, 200)
        self._total_usage_liters = self._monthly_usage_liters + random.uniform(10000, 50000)
    
    @property
    def flow_rate(self):
        return self._flow_rate
    
    @property
    def total_usage(self):
        return self._total_usage_liters
    
    @property
    def daily_usage(self):
        return self._daily_usage_liters
    
    @property
    def monthly_usage(self):
        return self._monthly_usage_liters
    
    @property
    def is_flowing(self):
        return self._is_flowing
    
    def _simulate_water_usage(self):
        """Simulate realistic water usage patterns
        
        Average household water usage in Romania: ~100-150 liters/person/day
        For a typical household: ~300-400 liters/day total
        
        This simulation uses probability-based events that represent
        realistic daily consumption distributed across time.
        """
        # Only simulate if valve is open
        if not self._valve_open:
            self._is_flowing = False
            self._flow_rate = 0.0
            return
        
        # Calculate usage probability based on source type
        # Lower probability = more realistic daily totals
        # With ~1000 updates/day (every ~90s), we need low probabilities
        
        if self._water_source == "bathroom":
            # Bathroom: ~80-120 L/day (showers, toilet, sink)
            # ~10-15 usage events per day
            usage_chance = 0.015  # ~15 events per 1000 updates
            if random.random() < usage_chance:
                self._is_flowing = True
                usage_type = random.choices(
                    ["shower", "toilet", "tap"],
                    weights=[0.15, 0.5, 0.35]  # More toilet flushes
                )[0]
                if usage_type == "shower":
                    self._flow_rate = random.uniform(8, 12)
                    usage = random.uniform(40, 80)  # 40-80L per shower
                elif usage_type == "toilet":
                    self._flow_rate = random.uniform(6, 9)
                    usage = random.uniform(4, 9)  # 4-9L per flush
                else:  # tap
                    self._flow_rate = random.uniform(4, 8)
                    usage = random.uniform(1, 5)  # 1-5L per use
            else:
                self._is_flowing = False
                self._flow_rate = 0.0
                usage = 0
                
        elif self._water_source == "kitchen":
            # Kitchen: ~50-80 L/day (cooking, dishes, drinking)
            usage_chance = 0.012
            if random.random() < usage_chance:
                self._is_flowing = True
                self._flow_rate = random.uniform(3, 8)
                usage = random.uniform(2, 15)  # 2-15L per use
            else:
                self._is_flowing = False
                self._flow_rate = 0.0
                usage = 0
                
        elif self._water_source == "garden":
            # Garden: ~0-100 L/day (seasonal, not daily)
            usage_chance = 0.005  # Less frequent
            if random.random() < usage_chance:
                self._is_flowing = True
                self._flow_rate = random.uniform(10, 20)
                usage = random.uniform(20, 100)  # 20-100L when watering
            else:
                self._is_flowing = False
                self._flow_rate = 0.0
                usage = 0
        else:  # main meter - aggregate
            # Main: tracks all sources, ~150-300 L/day
            usage_chance = 0.02
            if random.random() < usage_chance:
                self._is_flowing = True
                self._flow_rate = random.uniform(5, 12)
                usage = random.uniform(5, 30)
            else:
                self._is_flowing = False
                self._flow_rate = 0.0
                usage = 0
        
        # Add usage if any
        if usage > 0:
            self._daily_usage_liters += usage
            self._monthly_usage_liters += usage
            self._total_usage_liters += usage
            self._last_usage_time = datetime.now().timestamp()
        
        # Simulate pressure fluctuations (smaller changes)
        self._pressure_bar += random.uniform(-0.1, 0.1)
        self._pressure_bar = max(1.5, min(5.0, self._pressure_bar))
        
        # Water temperature varies slightly
        self._temperature_c += random.uniform(-1, 1)
        self._temperature_c = max(8, min(25, self._temperature_c))
    
    def _get_payload(self):
        self._simulate_water_usage()
        
        return {
            "flow_rate": round(self._flow_rate, 2),
            "is_flowing": self._is_flowing,
            "daily_usage": round(self._daily_usage_liters, 1),
            "monthly_usage": round(self._monthly_usage_liters, 1),
            "total_usage": round(self._total_usage_liters, 1),
            "pressure_bar": round(self._pressure_bar, 2),
            "temperature_c": round(self._temperature_c, 1),
            "valve_open": self._valve_open,
            "water_source": self._water_source,
            "leak_detected": self._leak_detected
        }
    
    def _get_device_specific_issue(self):
        # Leak detection (continuous low flow when no one should be using water)
        if random.random() < 0.02:  # 2% chance to simulate leak
            self._leak_detected = True
            self._current_issue = DeviceIssue.LEAK_DETECTED
            self._status = DeviceStatus.ERROR
            return DeviceIssue.LEAK_DETECTED
        
        # High flow warning (potential burst pipe or left tap)
        if self._flow_rate > 18:
            self._current_issue = DeviceIssue.HIGH_FLOW
            self._status = DeviceStatus.WARNING
            return DeviceIssue.HIGH_FLOW
        
        # Abnormal usage (much higher than daily average)
        if self._daily_usage_liters > 500:  # More than 500L in a day
            self._current_issue = DeviceIssue.ABNORMAL_USAGE
            self._status = DeviceStatus.WARNING
            return DeviceIssue.ABNORMAL_USAGE
        
        # Clear leak if it was a false alarm
        if self._leak_detected and random.random() < 0.3:
            self._leak_detected = False
            self._current_issue = DeviceIssue.NONE
            self._status = DeviceStatus.ONLINE
        
        return None
    
    def close_valve(self):
        """Emergency valve shutoff"""
        self._valve_open = False
        self._flow_rate = 0
        self._is_flowing = False
        return True
    
    def open_valve(self):
        """Open the water valve"""
        self._valve_open = True
        return True
    
    def reset_daily(self):
        """Reset daily usage counter"""
        self._daily_usage_liters = 0
        return True
    
    def reset_monthly(self):
        """Reset monthly usage counter"""
        self._monthly_usage_liters = 0
        return True
    
    def acknowledge_leak(self):
        """Acknowledge and clear leak warning after inspection"""
        self._leak_detected = False
        self._current_issue = DeviceIssue.NONE
        self._status = DeviceStatus.ONLINE
        return True
    
    def execute_command(self, command, **kwargs):
        if command == "close_valve":
            return "closed" if self.close_valve() else "failed"
        if command == "open_valve":
            return "opened" if self.open_valve() else "failed"
        if command == "reset_daily":
            self.reset_daily()
            return "daily reset"
        if command == "reset_monthly":
            self.reset_monthly()
            return "monthly reset"
        if command == "ack_leak":
            return "acknowledged" if self.acknowledge_leak() else "failed"
        return "?"


# ============================================================================
# Device Factory - Create devices from configuration
# ============================================================================

def create_device(device_type: str, device_id: str, name: str, location: str, **kwargs):
    """Factory function to create devices by type"""
    device_type = device_type.upper()
    
    if device_type == "BULB":
        device = SmartBulb(device_id, name, location)
        if "brightness" in kwargs:
            device.brightness = kwargs["brightness"]
        if "is_on" in kwargs:
            device.is_on = kwargs["is_on"]
        return device
    
    elif device_type == "THERMOSTAT":
        device = SmartThermostat(device_id, name, location)
        if "target_temp" in kwargs:
            device.target_temp = kwargs["target_temp"]
        if "current_temp" in kwargs:
            device.current_temp = kwargs["current_temp"]
        return device
    
    elif device_type == "CAMERA":
        device = SmartCamera(device_id, name, location)
        if "battery_level" in kwargs:
            device.battery_level = kwargs["battery_level"]
        return device
    
    elif device_type == "WATER_METER":
        device = SmartWaterMeter(device_id, name, location)
        if "water_source" in kwargs:
            device._water_source = kwargs["water_source"]
        return device
    
    else:
        raise ValueError(f"Unknown device type: {device_type}")
