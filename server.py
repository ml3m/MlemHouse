#!/usr/bin/env python3
"""MlemHouse Dashboard Server - Professional IoT Management Interface"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from devices import (
    SmartBulb, SmartThermostat, SmartCamera, SmartWaterMeter,
    DeviceStatus, DeviceIssue, create_device
)
from storage import StorageWorker
from analytics import process_updates, AnalyticsPipeline, make_reading
from config import (
    UTILITY_RATES, CURRENCY, DEVICE_ENERGY, HEATING_CONFIG, CARBON_FOOTPRINT,
    TIME_SIMULATION,
    format_currency, calculate_electricity_cost, calculate_gas_cost, calculate_water_cost
)


# ============================================================================
# Data Models
# ============================================================================

class DeviceCommand(BaseModel):
    device_id: str
    command: str
    params: Optional[Dict] = None


class DeviceUpdate(BaseModel):
    device_id: str
    property: str
    value: float | int | bool | str


class NewDevice(BaseModel):
    device_id: str
    device_type: str
    name: str
    location: str
    properties: Optional[Dict] = None


# ============================================================================
# Device Storage - JSON persistence
# ============================================================================

DEVICES_FILE = "devices.json"

def load_devices_config() -> List[dict]:
    """Load device configuration from JSON file"""
    if not os.path.exists(DEVICES_FILE):
        return get_default_devices_config()
    
    try:
        with open(DEVICES_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return get_default_devices_config()


def save_devices_config(devices: List[dict]):
    """Save device configuration to JSON file"""
    with open(DEVICES_FILE, 'w') as f:
        json.dump(devices, f, indent=2)


def get_default_devices_config() -> List[dict]:
    """Default device configuration for MlemHouse"""
    return [
        # Lights
        {"device_id": "bulb_001", "device_type": "BULB", "name": "Living Room Light", "location": "Living Room", "properties": {"brightness": 80, "is_on": True}},
        {"device_id": "bulb_002", "device_type": "BULB", "name": "Bedroom Light", "location": "Bedroom", "properties": {"brightness": 100, "is_on": False}},
        {"device_id": "bulb_003", "device_type": "BULB", "name": "Kitchen Light", "location": "Kitchen", "properties": {"brightness": 100, "is_on": True}},
        {"device_id": "bulb_004", "device_type": "BULB", "name": "Bathroom Light", "location": "Bathroom", "properties": {"brightness": 100, "is_on": False}},
        # Thermostats
        {"device_id": "thermo_001", "device_type": "THERMOSTAT", "name": "Main Thermostat", "location": "Living Room", "properties": {"current_temp": 22.5, "target_temp": 23.0}},
        {"device_id": "thermo_002", "device_type": "THERMOSTAT", "name": "Bedroom Climate", "location": "Bedroom", "properties": {"current_temp": 21.0, "target_temp": 22.0}},
        # Cameras
        {"device_id": "cam_001", "device_type": "CAMERA", "name": "Front Door Cam", "location": "Entrance", "properties": {"battery_level": 78}},
        {"device_id": "cam_002", "device_type": "CAMERA", "name": "Backyard Cam", "location": "Backyard", "properties": {"battery_level": 45}},
        {"device_id": "cam_003", "device_type": "CAMERA", "name": "Garage Cam", "location": "Garage", "properties": {"battery_level": 92}},
        # Water Meters
        {"device_id": "water_001", "device_type": "WATER_METER", "name": "Main Water Meter", "location": "Utility Room", "properties": {"water_source": "main"}},
        {"device_id": "water_002", "device_type": "WATER_METER", "name": "Bathroom Water", "location": "Bathroom", "properties": {"water_source": "bathroom"}},
        {"device_id": "water_003", "device_type": "WATER_METER", "name": "Kitchen Water", "location": "Kitchen", "properties": {"water_source": "kitchen"}},
        {"device_id": "water_004", "device_type": "WATER_METER", "name": "Garden Irrigation", "location": "Garden", "properties": {"water_source": "garden"}},
    ]


# ============================================================================
# Device Manager - Singleton to manage all devices
# ============================================================================

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, any] = {}
        self.readings: List[dict] = []
        self.storage: Optional[StorageWorker] = None
        self._running = False
        self._tasks = []
        self._websockets: List[WebSocket] = []
        self._alerts: List[dict] = []
        self._max_alerts = 50
        self._start_time = datetime.now()
        
        # Energy tracking (accumulated)
        self._electricity_kwh = 0.0
        self._gas_kwh = 0.0
        self._water_liters = 0.0
        self._last_energy_update = datetime.now()
        
        # Time simulation
        self._time_multiplier = 1  # 1 = real-time
        self._simulated_hours = 0.0  # Total simulated hours elapsed
        self._experimental_mode = False
        
        # Device configurations (custom wattage, etc.)
        self._device_configs: Dict[str, dict] = {}
        
    def initialize_devices(self):
        """Load and create devices from configuration"""
        config = load_devices_config()
        
        for dev_config in config:
            try:
                props = dev_config.get("properties", {})
                device = create_device(
                    dev_config["device_type"],
                    dev_config["device_id"],
                    dev_config["name"],
                    dev_config["location"],
                    **props
                )
                self.devices[device.device_id] = device
            except Exception as e:
                print(f"Error creating device {dev_config.get('device_id')}: {e}")
        
        print(f"Loaded {len(self.devices)} devices")
    
    def save_devices(self):
        """Save current device configuration"""
        config = []
        for dev in self.devices.values():
            dev_config = {
                "device_id": dev.device_id,
                "device_type": dev.device_type,
                "name": dev.name,
                "location": dev.location,
                "properties": {}
            }
            
            # Save device-specific properties
            if dev.device_type == "BULB":
                dev_config["properties"] = {
                    "brightness": dev.brightness,
                    "is_on": dev.is_on
                }
            elif dev.device_type == "THERMOSTAT":
                dev_config["properties"] = {
                    "target_temp": dev.target_temp,
                    "current_temp": dev.current_temp
                }
            elif dev.device_type == "CAMERA":
                dev_config["properties"] = {
                    "battery_level": dev.battery_level
                }
            elif dev.device_type == "WATER_METER":
                dev_config["properties"] = {
                    "water_source": dev._water_source
                }
            
            config.append(dev_config)
        
        save_devices_config(config)
    
    def add_device(self, dev_config: dict):
        """Add a new device"""
        props = dev_config.get("properties", {})
        device = create_device(
            dev_config["device_type"],
            dev_config["device_id"],
            dev_config["name"],
            dev_config["location"],
            **props
        )
        self.devices[device.device_id] = device
        self.save_devices()
        return device
    
    def remove_device(self, device_id: str) -> bool:
        """Remove a device"""
        if device_id in self.devices:
            del self.devices[device_id]
            self.save_devices()
            return True
        return False
    
    def get_device(self, device_id: str):
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[dict]:
        """Get all devices with their current state"""
        result = []
        for dev in self.devices.values():
            result.append(self._device_to_dict(dev))
        return result
    
    def _device_to_dict(self, dev) -> dict:
        """Convert device to dictionary for JSON serialization"""
        # Get custom config for this device
        config = self._device_configs.get(dev.device_id, {})
        
        base = {
            "device_id": dev.device_id,
            "name": dev.name,
            "location": dev.location,
            "device_type": dev.device_type,
            "is_connected": dev.is_connected,
            "signal_strength": dev.signal_strength,
            "status": dev.status.value,
            "issue": dev.current_issue.value,
        }
        
        if dev.device_type == "BULB":
            max_watts = config.get("max_watts", DEVICE_ENERGY["BULB"]["max_watts"])
            standby_watts = config.get("standby_watts", DEVICE_ENERGY["BULB"]["standby_watts"])
            power_draw = (dev.brightness / 100) * max_watts if dev.is_on else standby_watts
            base.update({
                "is_on": dev.is_on,
                "brightness": dev.brightness,
                "power_draw": round(power_draw, 2),
                "max_watts": max_watts,
                "standby_watts": standby_watts,
            })
        elif dev.device_type == "THERMOSTAT":
            base.update({
                "current_temp": round(dev.current_temp, 1),
                "target_temp": dev.target_temp,
                "humidity": round(dev.humidity, 1),
                "hvac_mode": getattr(dev, '_hvac_mode', 'auto'),
                "heating_kwh_per_degree": config.get("heating_kwh_per_degree", DEVICE_ENERGY["THERMOSTAT"]["heating_kwh_per_degree"]),
            })
        elif dev.device_type == "CAMERA":
            base.update({
                "motion_detected": dev.motion_detected,
                "battery_level": round(dev.battery_level, 1),
                "last_snapshot": dev.last_snapshot,
                "recording": getattr(dev, '_recording', False),
                "storage_percent": round(dev.storage_percent, 1),
                "active_watts": config.get("active_watts", DEVICE_ENERGY["CAMERA"]["active_watts"]),
                "recording_watts": config.get("recording_watts", DEVICE_ENERGY["CAMERA"]["recording_watts"]),
            })
        elif dev.device_type == "WATER_METER":
            base.update({
                "flow_rate": round(dev.flow_rate, 2),
                "is_flowing": dev.is_flowing,
                "daily_usage": round(dev.daily_usage, 1),
                "monthly_usage": round(dev.monthly_usage, 1),
                "water_source": dev._water_source,
                "valve_open": dev._valve_open,
                "leak_detected": dev._leak_detected,
                "pressure_bar": round(dev._pressure_bar, 2),
            })
        
        return base
    
    async def connect_all_devices(self):
        """Connect all devices concurrently"""
        async with asyncio.TaskGroup() as tg:
            for dev in self.devices.values():
                tg.create_task(dev.connect())
    
    async def connect_device(self, device_id: str):
        """Connect a single device"""
        dev = self.devices.get(device_id)
        if dev:
            await dev.connect()
            # Start update loop for this device
            task = asyncio.create_task(self._device_update_loop(dev))
            self._tasks.append(task)
    
    async def broadcast(self, message: dict):
        """Send message to all connected WebSocket clients"""
        dead = []
        for ws in self._websockets:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        for ws in dead:
            self._websockets.remove(ws)
    
    def add_alert(self, alert: dict):
        """Add alert and maintain max size"""
        self._alerts.insert(0, alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[:self._max_alerts]
    
    def _update_energy_tracking(self):
        """Update energy consumption tracking with time multiplier support"""
        now = datetime.now()
        real_elapsed_hours = (now - self._last_energy_update).total_seconds() / 3600
        self._last_energy_update = now
        
        if real_elapsed_hours <= 0:
            return
        
        # Apply time multiplier for simulation
        simulated_hours = real_elapsed_hours * self._time_multiplier
        self._simulated_hours += simulated_hours
        
        # Calculate electricity consumption
        total_watts = 0
        for dev in self.devices.values():
            if not dev.is_connected:
                continue
            
            config = self._device_configs.get(dev.device_id, {})
            
            if dev.device_type == "BULB":
                max_watts = config.get("max_watts", DEVICE_ENERGY["BULB"]["max_watts"])
                standby_watts = config.get("standby_watts", DEVICE_ENERGY["BULB"]["standby_watts"])
                watts = (dev.brightness / 100) * max_watts if dev.is_on else standby_watts
                total_watts += watts
            elif dev.device_type == "THERMOSTAT":
                total_watts += DEVICE_ENERGY["THERMOSTAT"]["device_watts"]
            elif dev.device_type == "CAMERA":
                recording_watts = config.get("recording_watts", DEVICE_ENERGY["CAMERA"]["recording_watts"])
                standby_watts = config.get("standby_watts", DEVICE_ENERGY["CAMERA"]["standby_watts"])
                watts = recording_watts if getattr(dev, '_recording', False) else standby_watts
                total_watts += watts
            elif dev.device_type == "WATER_METER":
                total_watts += DEVICE_ENERGY["WATER_METER"]["active_watts"]
        
        self._electricity_kwh += (total_watts / 1000) * simulated_hours
        
        # Calculate gas consumption (heating) - more realistic calculation
        for dev in self.devices.values():
            if dev.device_type == "THERMOSTAT" and dev.is_connected:
                config = self._device_configs.get(dev.device_id, {})
                heating_rate = config.get("heating_kwh_per_degree", DEVICE_ENERGY["THERMOSTAT"]["heating_kwh_per_degree"])
                
                # Heat loss calculation: energy needed to maintain indoor temp vs outside
                outside_temp = HEATING_CONFIG["outside_temp_current"]
                current_temp = dev.current_temp
                target_temp = dev.target_temp
                
                # If heating is needed (target > current, or maintaining against cold outside)
                hvac_mode = getattr(dev, '_hvac_mode', 'auto')
                if hvac_mode in ['heat', 'auto'] and current_temp < target_temp + 1:
                    # Heat loss based on difference from outside temp
                    temp_differential = max(0, current_temp - outside_temp)
                    # More realistic: heat loss is proportional to temp differential
                    heat_loss_kw = temp_differential * HEATING_CONFIG["heat_loss_coefficient"]
                    gas_kwh = (heat_loss_kw * simulated_hours) / HEATING_CONFIG["boiler_efficiency"]
                    self._gas_kwh += gas_kwh
    
    async def _device_update_loop(self, dev):
        """Individual device update loop with time multiplier support"""
        import random
        while self._running:
            # Adjust sleep time based on time multiplier (faster updates when fast-forwarding)
            base_interval = random.uniform(1.5, 4.0)
            sleep_time = max(0.1, base_interval / max(1, self._time_multiplier / 10))
            await asyncio.sleep(sleep_time)
            if not self._running or not dev.is_connected:
                continue
            
            update = await dev.send_update()
            if update:
                self.readings.append(update)
                if len(self.readings) > 1000:
                    self.readings = self.readings[-500:]
                
                if self.storage:
                    self.storage.enqueue(update)
                
                # Track water usage
                if dev.device_type == "WATER_METER":
                    payload = update.get("payload", {})
                    # Water is tracked in the device itself
                
                # Check for issues and create alerts
                issue = update.get("issue", "none")
                if issue != "none" and issue != "motion_alert":
                    alert = {
                        "id": f"alert_{datetime.now().timestamp()}",
                        "device_id": dev.device_id,
                        "device_name": dev.name,
                        "device_type": dev.device_type,
                        "issue": issue,
                        "timestamp": datetime.now().isoformat(),
                        "severity": "error" if issue in ["critical_battery", "connection_lost", "sensor_malfunction", "leak_detected"] else "warning"
                    }
                    self.add_alert(alert)
                    await self.broadcast({"type": "alert", "data": alert})
                
                # Broadcast device update
                await self.broadcast({
                    "type": "device_update",
                    "data": self._device_to_dict(dev)
                })
    
    async def _metrics_broadcast_loop(self):
        """Periodically broadcast aggregated metrics"""
        while self._running:
            await asyncio.sleep(2.0)
            if not self._running:
                break
            
            self._update_energy_tracking()
            metrics = self.get_metrics()
            await self.broadcast({
                "type": "metrics_update",
                "data": metrics
            })
    
    def get_metrics(self) -> dict:
        """Calculate current metrics including costs"""
        devices = list(self.devices.values())
        
        # Current power draw (Watts)
        current_power_watts = 0
        for d in devices:
            if not d.is_connected:
                continue
            if d.device_type == "BULB":
                current_power_watts += (d.brightness / 100) * 10 if d.is_on else 0.5
            elif d.device_type == "CAMERA":
                current_power_watts += 8 if getattr(d, '_recording', False) else 2
            elif d.device_type == "THERMOSTAT":
                current_power_watts += 3
            elif d.device_type == "WATER_METER":
                current_power_watts += 1
        
        # Temperature average
        thermos = [d for d in devices if d.device_type == "THERMOSTAT" and d.is_connected]
        avg_temp = sum(d.current_temp for d in thermos) / len(thermos) if thermos else 0
        
        # Heating status
        heating_active = any(d.target_temp > d.current_temp and d._hvac_mode in ['heat', 'auto'] 
                           for d in thermos)
        
        # Battery average
        cams = [d for d in devices if d.device_type == "CAMERA"]
        avg_battery = sum(d.battery_level for d in cams) / len(cams) if cams else 0
        
        # Water metrics
        water_meters = [d for d in devices if d.device_type == "WATER_METER"]
        total_water_daily = sum(d.daily_usage for d in water_meters)
        total_water_monthly = sum(d.monthly_usage for d in water_meters)
        water_flowing = any(d.is_flowing for d in water_meters)
        current_flow_rate = sum(d.flow_rate for d in water_meters)
        
        # Device counts
        online = sum(1 for d in devices if d.is_connected)
        with_issues = sum(1 for d in devices if d.current_issue != DeviceIssue.NONE)
        
        # Lights status
        bulbs = [d for d in devices if d.device_type == "BULB"]
        lights_on = sum(1 for d in bulbs if d.is_on)
        total_lights = len(bulbs)
        
        # Uptime
        uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        
        # Cost calculations (Romanian lei)
        electricity_cost = calculate_electricity_cost(self._electricity_kwh)
        gas_cost = calculate_gas_cost(self._gas_kwh)
        water_cost = calculate_water_cost(total_water_monthly)
        total_cost = electricity_cost + gas_cost + water_cost
        
        # Estimated monthly costs - based on SIMULATED hours, not real time
        # This ensures estimates stay realistic regardless of time multiplier
        simulated_hours = self._simulated_hours if self._simulated_hours > 0.01 else uptime_seconds / 3600
        
        if simulated_hours > 0.01:  # At least ~36 seconds of simulated time
            # Calculate hourly rates from accumulated usage
            hourly_elec_cost = electricity_cost / simulated_hours
            hourly_gas_cost = gas_cost / simulated_hours
            hourly_water_cost = water_cost / simulated_hours
            
            # Extrapolate to monthly (30 days * 24 hours = 720 hours)
            est_monthly_electricity = hourly_elec_cost * 720
            est_monthly_gas = hourly_gas_cost * 720
            est_monthly_water = hourly_water_cost * 720
            est_monthly_total = est_monthly_electricity + est_monthly_gas + est_monthly_water
            
            # Apply reasonable caps for Romanian household
            # Typical monthly: ~200-500 lei electricity, ~100-300 lei gas, ~50-150 lei water
            est_monthly_electricity = min(est_monthly_electricity, 2000)  # Max 2000 lei
            est_monthly_gas = min(est_monthly_gas, 1500)  # Max 1500 lei
            est_monthly_water = min(est_monthly_water, 500)  # Max 500 lei
            est_monthly_total = est_monthly_electricity + est_monthly_gas + est_monthly_water
        else:
            est_monthly_electricity = est_monthly_gas = est_monthly_water = est_monthly_total = 0
        
        # Carbon footprint
        carbon_kg = (
            self._electricity_kwh * CARBON_FOOTPRINT["electricity"] +
            self._gas_kwh * CARBON_FOOTPRINT["gas"] +
            total_water_monthly * CARBON_FOOTPRINT["water"]
        )
        
        return {
            # Device stats
            "total_devices": len(devices),
            "online_devices": online,
            "offline_devices": len(devices) - online,
            "devices_with_issues": with_issues,
            
            # Power
            "current_power_watts": round(current_power_watts, 1),
            "electricity_kwh": round(self._electricity_kwh, 3),
            
            # Temperature
            "average_temperature": round(avg_temp, 1),
            "heating_active": heating_active,
            "gas_kwh": round(self._gas_kwh, 3),
            
            # Water
            "water_daily_liters": round(total_water_daily, 1),
            "water_monthly_liters": round(total_water_monthly, 1),
            "water_monthly_m3": round(total_water_monthly / 1000, 2),
            "water_flowing": water_flowing,
            "current_flow_rate": round(current_flow_rate, 1),
            
            # Lights
            "lights_on": lights_on,
            "total_lights": total_lights,
            
            # Battery
            "average_battery": round(avg_battery, 1),
            
            # Costs (current session)
            "electricity_cost": round(electricity_cost, 2),
            "gas_cost": round(gas_cost, 2),
            "water_cost": round(water_cost, 2),
            "total_cost": round(total_cost, 2),
            
            # Estimated monthly costs
            "est_monthly_electricity": round(est_monthly_electricity, 2),
            "est_monthly_gas": round(est_monthly_gas, 2),
            "est_monthly_water": round(est_monthly_water, 2),
            "est_monthly_total": round(est_monthly_total, 2),
            
            # Carbon footprint
            "carbon_kg": round(carbon_kg, 2),
            
            # Rates info
            "electricity_rate": UTILITY_RATES["electricity"]["rate_avg"],
            "gas_rate": UTILITY_RATES["gas"]["rate"],
            "water_rate": UTILITY_RATES["water"]["total_rate"],
            "currency": CURRENCY["symbol"],
            
            # System
            "total_readings": len(self.readings),
            "active_alerts": len([a for a in self._alerts if a.get("severity") == "error"]),
            "uptime_seconds": int(uptime_seconds),
            
            # Time simulation
            "time_multiplier": self._time_multiplier,
            "simulated_hours": round(self._simulated_hours, 2),
            "experimental_mode": self._experimental_mode,
        }
    
    async def start(self):
        """Start the device simulation"""
        self._running = True
        self._start_time = datetime.now()
        self._last_energy_update = datetime.now()
        self.storage = StorageWorker("history.log")
        self.storage.start()
        
        await self.connect_all_devices()
        
        for dev in self.devices.values():
            task = asyncio.create_task(self._device_update_loop(dev))
            self._tasks.append(task)
        
        self._tasks.append(asyncio.create_task(self._metrics_broadcast_loop()))
    
    async def stop(self):
        """Stop the device simulation"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self.storage:
            self.storage.stop()
        self._tasks = []
        self.save_devices()


# Global device manager
device_manager = DeviceManager()


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    device_manager.initialize_devices()
    await device_manager.start()
    print("🏠 MlemHouse Dashboard Started")
    yield
    await device_manager.stop()
    print("👋 MlemHouse Dashboard Stopped")


app = FastAPI(
    title="MlemHouse IoT Dashboard",
    description="Professional IoT Device Management System - Timișoara, Romania",
    version="3.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ============================================================================
# Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "devices": device_manager.get_all_devices(),
        "metrics": device_manager.get_metrics()
    })


@app.get("/api/devices")
async def get_devices():
    """Get all devices"""
    return {"devices": device_manager.get_all_devices()}


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Get specific device"""
    dev = device_manager.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_manager._device_to_dict(dev)


@app.post("/api/devices")
async def create_new_device(new_device: NewDevice):
    """Create a new device"""
    if device_manager.get_device(new_device.device_id):
        raise HTTPException(status_code=400, detail="Device ID already exists")
    
    try:
        dev_config = {
            "device_id": new_device.device_id,
            "device_type": new_device.device_type,
            "name": new_device.name,
            "location": new_device.location,
            "properties": new_device.properties or {}
        }
        device = device_manager.add_device(dev_config)
        
        # Connect and start the device
        await device_manager.connect_device(new_device.device_id)
        
        await device_manager.broadcast({
            "type": "device_added",
            "data": device_manager._device_to_dict(device)
        })
        
        return {"status": "ok", "device": device_manager._device_to_dict(device)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str):
    """Delete a device"""
    if not device_manager.get_device(device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_manager.remove_device(device_id)
    
    await device_manager.broadcast({
        "type": "device_removed",
        "data": {"device_id": device_id}
    })
    
    return {"status": "ok"}


@app.post("/api/devices/{device_id}/command")
async def send_command(device_id: str, cmd: DeviceCommand):
    """Send command to device"""
    dev = device_manager.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    
    params = cmd.params or {}
    result = dev.execute_command(cmd.command, **params)
    
    # Broadcast update
    await device_manager.broadcast({
        "type": "device_update",
        "data": device_manager._device_to_dict(dev)
    })
    
    return {"status": "ok", "result": result}


@app.post("/api/devices/{device_id}/update")
async def update_device(device_id: str, update: DeviceUpdate):
    """Update device property"""
    dev = device_manager.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    
    prop = update.property
    val = update.value
    
    if hasattr(dev, prop):
        setattr(dev, prop, val)
    elif hasattr(dev, f"_{prop}"):
        setattr(dev, prop, val)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown property: {prop}")
    
    await device_manager.broadcast({
        "type": "device_update",
        "data": device_manager._device_to_dict(dev)
    })
    
    return {"status": "ok"}


@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics"""
    return device_manager.get_metrics()


@app.get("/api/costs")
async def get_costs():
    """Get detailed cost breakdown"""
    metrics = device_manager.get_metrics()
    return {
        "current": {
            "electricity": metrics["electricity_cost"],
            "gas": metrics["gas_cost"],
            "water": metrics["water_cost"],
            "total": metrics["total_cost"]
        },
        "estimated_monthly": {
            "electricity": metrics["est_monthly_electricity"],
            "gas": metrics["est_monthly_gas"],
            "water": metrics["est_monthly_water"],
            "total": metrics["est_monthly_total"]
        },
        "rates": {
            "electricity": f"{metrics['electricity_rate']} lei/kWh",
            "gas": f"{metrics['gas_rate']} lei/kWh",
            "water": f"{metrics['water_rate']} lei/m³"
        },
        "usage": {
            "electricity_kwh": metrics["electricity_kwh"],
            "gas_kwh": metrics["gas_kwh"],
            "water_m3": metrics["water_monthly_m3"]
        },
        "carbon_footprint_kg": metrics["carbon_kg"]
    }


@app.get("/api/alerts")
async def get_alerts():
    """Get recent alerts"""
    return {"alerts": device_manager._alerts}


@app.delete("/api/alerts/{alert_id}")
async def dismiss_alert(alert_id: str):
    """Dismiss an alert"""
    device_manager._alerts = [a for a in device_manager._alerts if a.get("id") != alert_id]
    return {"status": "ok"}


@app.delete("/api/alerts")
async def clear_alerts():
    """Clear all alerts"""
    device_manager._alerts = []
    await device_manager.broadcast({"type": "alerts_cleared"})
    return {"status": "ok"}


@app.get("/api/history")
async def get_history(limit: int = 100):
    """Get reading history"""
    readings = device_manager.readings[-limit:]
    return {"readings": readings, "total": len(device_manager.readings)}


@app.get("/api/analytics")
async def get_analytics():
    """Get analytics data"""
    if not device_manager.readings:
        return {"metrics": {}, "critical_events": [], "total_readings": 0}
    return process_updates(device_manager.readings[-500:])


@app.get("/api/config/rates")
async def get_rates():
    """Get current utility rates"""
    return {
        "electricity": UTILITY_RATES["electricity"],
        "gas": UTILITY_RATES["gas"],
        "water": UTILITY_RATES["water"],
        "currency": CURRENCY
    }


# ============================================================================
# Settings & Time Simulation
# ============================================================================

class SettingsUpdate(BaseModel):
    experimental_mode: Optional[bool] = None
    time_multiplier: Optional[int] = None


class DeviceConfigUpdate(BaseModel):
    max_watts: Optional[float] = None
    standby_watts: Optional[float] = None
    heating_kwh_per_degree: Optional[float] = None
    active_watts: Optional[float] = None
    recording_watts: Optional[float] = None


@app.get("/api/settings")
async def get_settings():
    """Get current settings"""
    return {
        "experimental_mode": device_manager._experimental_mode,
        "time_multiplier": device_manager._time_multiplier,
        "available_multipliers": TIME_SIMULATION["multipliers"],
        "multiplier_labels": TIME_SIMULATION["labels"],
        "simulated_hours": round(device_manager._simulated_hours, 2),
    }


@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update settings"""
    if settings.experimental_mode is not None:
        device_manager._experimental_mode = settings.experimental_mode
    
    if settings.time_multiplier is not None:
        if settings.time_multiplier in TIME_SIMULATION["multipliers"]:
            device_manager._time_multiplier = settings.time_multiplier
        else:
            raise HTTPException(status_code=400, detail="Invalid time multiplier")
    
    await device_manager.broadcast({
        "type": "settings_update",
        "data": {
            "experimental_mode": device_manager._experimental_mode,
            "time_multiplier": device_manager._time_multiplier,
        }
    })
    
    return {"status": "ok", "settings": await get_settings()}


@app.get("/api/devices/{device_id}/config")
async def get_device_config(device_id: str):
    """Get device configuration"""
    dev = device_manager.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    
    config = device_manager._device_configs.get(device_id, {})
    
    # Return defaults merged with custom config
    if dev.device_type == "BULB":
        return {
            "max_watts": config.get("max_watts", DEVICE_ENERGY["BULB"]["max_watts"]),
            "standby_watts": config.get("standby_watts", DEVICE_ENERGY["BULB"]["standby_watts"]),
            "configurable_max": DEVICE_ENERGY["BULB"]["configurable_max"],
        }
    elif dev.device_type == "THERMOSTAT":
        return {
            "heating_kwh_per_degree": config.get("heating_kwh_per_degree", DEVICE_ENERGY["THERMOSTAT"]["heating_kwh_per_degree"]),
        }
    elif dev.device_type == "CAMERA":
        return {
            "active_watts": config.get("active_watts", DEVICE_ENERGY["CAMERA"]["active_watts"]),
            "standby_watts": config.get("standby_watts", DEVICE_ENERGY["CAMERA"]["standby_watts"]),
            "recording_watts": config.get("recording_watts", DEVICE_ENERGY["CAMERA"]["recording_watts"]),
        }
    
    return {}


@app.put("/api/devices/{device_id}/config")
async def update_device_config(device_id: str, config: DeviceConfigUpdate):
    """Update device configuration (watts, etc.)"""
    dev = device_manager.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device_id not in device_manager._device_configs:
        device_manager._device_configs[device_id] = {}
    
    # Update only provided values
    config_dict = config.model_dump(exclude_none=True)
    device_manager._device_configs[device_id].update(config_dict)
    
    # Broadcast update
    await device_manager.broadcast({
        "type": "device_update",
        "data": device_manager._device_to_dict(dev)
    })
    
    return {"status": "ok", "config": device_manager._device_configs[device_id]}


@app.post("/api/simulation/reset")
async def reset_simulation():
    """Reset energy counters and simulated time"""
    device_manager._electricity_kwh = 0.0
    device_manager._gas_kwh = 0.0
    device_manager._simulated_hours = 0.0
    device_manager._start_time = datetime.now()
    
    # Reset water meters
    for dev in device_manager.devices.values():
        if dev.device_type == "WATER_METER":
            dev.reset_daily()
            dev.reset_monthly()
    
    await device_manager.broadcast({
        "type": "simulation_reset",
        "data": {}
    })
    
    return {"status": "ok"}


# ============================================================================
# WebSocket
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    device_manager._websockets.append(websocket)
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "devices": device_manager.get_all_devices(),
                "metrics": device_manager.get_metrics(),
                "alerts": device_manager._alerts
            }
        })
        
        while True:
            # Keep connection alive and handle incoming commands
            data = await websocket.receive_json()
            
            if data.get("type") == "command":
                device_id = data.get("device_id")
                command = data.get("command")
                params = data.get("params", {})
                
                dev = device_manager.get_device(device_id)
                if dev:
                    dev.execute_command(command, **params)
                    await device_manager.broadcast({
                        "type": "device_update",
                        "data": device_manager._device_to_dict(dev)
                    })
                    
    except WebSocketDisconnect:
        device_manager._websockets.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in device_manager._websockets:
            device_manager._websockets.remove(websocket)


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
