from abc import ABC, abstractmethod
import asyncio
import random
import time
import sys


class SmartDevice(ABC):
    
    def __init__(self, v_dev_id, v_name, v_location):
        self._dev_id = v_dev_id
        self._name = v_name
        self._location = v_location
        self._type = "GENERIC"
        self._connected = False
    
    @property
    def device_id(self):
        return self._dev_id
    
    @property
    def name(self):
        return self._name
    
    @property
    def location(self):
        return self._location
    
    @property
    def device_type(self):
        return self._type
    
    @property
    def is_connected(self):
        return self._connected
    
    async def connect(self):
        print(f"{self._name} is connecting...", flush=True)
        v_delay = random.uniform(0.5, 2.0)
        await asyncio.sleep(v_delay)
        self._connected = True
        print(f"{self._name} connected successfully in {v_delay:.2f}s.", flush=True)
    
    def send_update(self):
        return {
            "device_id": self._dev_id,
            "type": self._type,
            "timestamp": time.time(),
            "payload": self._get_state()
        }
    
    def _get_state(self):
        return {}
    
    @abstractmethod
    def execute_command(self, v_cmd, **kwargs):
        pass


class SmartBulb(SmartDevice):
    
    C_COMMANDS = {
        "on": lambda self, **kw: self._turn_on(),
        "off": lambda self, **kw: self._turn_off(),
        "dim": lambda self, **kw: self._set_brightness(kw.get("level", 50)),
    }
    
    def __init__(self, v_dev_id, v_name, v_location):
        super().__init__(v_dev_id, v_name, v_location)
        self._type = "BULB"
        self._on = True
        self._brightness = 100
        self._kwh = 0.0
        self._wattage = 12
    
    @property
    def is_on(self):
        return self._on
    
    @property
    def brightness(self):
        return self._brightness
    
    @brightness.setter
    def brightness(self, v_val):
        self._brightness = max(0, min(100, v_val))
    
    @property
    def kwh(self):
        return self._kwh
    
    def _turn_on(self):
        self._on = True
        return "Bulb turned on"
    
    def _turn_off(self):
        self._on = False
        return "Bulb turned off"
    
    def _set_brightness(self, v_level):
        self.brightness = v_level
        return f"Brightness: {self._brightness}"
    
    def _get_state(self):
        if random.random() < 0.2:
            self._on = not self._on
        if self._on:
            v_hours = random.uniform(0.0005, 0.002)
            self._kwh += (self._wattage * (self._brightness / 100) * v_hours) / 1000
            self._brightness = max(20, min(100, self._brightness + random.randint(-10, 10)))
        return {"is_on": self._on, "brightness": self._brightness, "kwh": round(self._kwh, 4)}
    
    def execute_command(self, v_cmd, **kwargs):
        v_handler = self.C_COMMANDS.get(v_cmd)
        if v_handler:
            return v_handler(self, **kwargs)
        return "unknown cmd"


class SmartThermostat(SmartDevice):
    
    def __init__(self, v_dev_id, v_name, v_location):
        super().__init__(v_dev_id, v_name, v_location)
        self._type = "THERMOSTAT"
        self._temp = random.uniform(18.0, 28.0)
        self._target = 24.0
        self._humidity = random.uniform(30.0, 60.0)
        self._kwh = 0.0
    
    @property
    def current_temp(self):
        return self._temp
    
    @property
    def target_temp(self):
        return self._target
    
    @target_temp.setter
    def target_temp(self, v_val):
        self._target = max(10, min(35, v_val))
    
    @property
    def humidity(self):
        return self._humidity
    
    @property
    def kwh(self):
        return self._kwh
    
    def _get_state(self):
        self._temp += random.uniform(-2.0, 2.0)
        self._humidity = random.uniform(30.0, 60.0)

        v_diff = abs(self._temp - self._target)
        if v_diff > 1:
            self._kwh += random.uniform(0.01, 0.05)
        return {
            "current_temp": self._temp,
            "target_temp": self._target,
            "humidity": self._humidity,
            "kwh": round(self._kwh, 4)
        }
    
    def execute_command(self, v_cmd, **kwargs):
        if v_cmd == "set":
            self.target_temp = kwargs.get("temp", 22.0)
            return f"Target set to {self._target}"
        
        if v_cmd == "cool":
            self.target_temp = self._target - 2
            return "Smart Thermostat command executed: Temperature adjusted."
        
        if v_cmd == "heat":
            self.target_temp = self._target + 2
            return f"Heating to {self._target}"


class SmartCamera(SmartDevice):
    def __init__(self, v_dev_id, v_name, v_location):
        super().__init__(v_dev_id, v_name, v_location)
        self._type = "CAMERA"
        self._motion = False
        self._battery = random.uniform(50.0, 100.0)
        self._snapshot_ts = time.time()
        self._armed = True
        self._recordings = 0
    
    @property
    def motion_detected(self):
        return self._motion
    
    @property
    def battery_level(self):
        return self._battery
    
    @property
    def last_snapshot(self):
        return self._snapshot_ts
    
    @property
    def recordings(self):
        return self._recordings
    
    def _get_state(self):
        self._motion = random.random() < 0.2
        self._battery = max(0, self._battery - random.uniform(0.1, 1.0))
        if self._motion:
            self._snapshot_ts = time.time()
            self._recordings += 1
        return {
            "motion_detected": self._motion,
            "last_snapshot": self._snapshot_ts,
            "battery_level": self._battery,
            "recordings": self._recordings
        }
    
    def execute_command(self, v_cmd, **kwargs):
        match v_cmd:
            case "snap":
                self._snapshot_ts = time.time()
                return "snapshot taken"
            case "arm":
                self._armed = True
                return "armed"
            case "disarm":
                self._armed = False
                return "disarmed"
            case "recharge":
                self._battery = 100.0
                return "recharged"
            case _:
                return None


class SmartFaucet(SmartDevice):
    
    def __init__(self, v_dev_id, v_name, v_location):
        super().__init__(v_dev_id, v_name, v_location)
        self._type = "FAUCET"
        self._flow = False
        self._liters = 0.0
        self._temp_setting = "warm"
    
    @property
    def is_flowing(self):
        return self._flow
    
    @property
    def liters_used(self):
        return self._liters
    
    @property
    def temp_setting(self):
        return self._temp_setting
    
    def _get_state(self):
        if random.random() < 0.3:
            self._flow = not self._flow
        if self._flow:
            self._liters += random.uniform(0.1, 0.5)
        return {
            "flowing": self._flow,
            "liters": round(self._liters, 2),
            "temp": self._temp_setting
        }
    
    def execute_command(self, v_cmd, **kwargs):
        match v_cmd:
            case "on":
                self._flow = True
                return "water on"
            case "off":
                self._flow = False
                return "water off"
            case "cold":
                self._temp_setting = "cold"
                return "set to cold"
            case "warm":
                self._temp_setting = "warm"
                return "set to warm"
            case "hot":
                self._temp_setting = "hot"
                return "set to hot"
            case "reset":
                self._liters = 0.0
                return "usage reset"
            case _:
                return None
