#!/usr/bin/env python3
"""ecohub main"""

import asyncio
import argparse
import signal
import sys

from devices import SmartDevice, SmartBulb, SmartThermostat, SmartCamera, SmartWaterMeter
from storage import StorageWorker, StorageStats
from network import NetworkController
from analytics import f_process_updates
from utils import f_print_report


def f_make_devices():
    v_devs = []
    
    v_b1 = SmartBulb("bulb1", "Living Room Light", "Living Room")
    v_b1.brightness = 100
    v_b1.is_on = True
    v_devs.append(v_b1)
    
    v_b2 = SmartBulb("bulb2", "Bedroom Light", "Bedroom")
    v_b2.brightness = 50
    v_b2.is_on = True
    v_devs.append(v_b2)
    
    v_t1 = SmartThermostat("thermo1", "Living Room Thermostat", "Living Room")
    v_t1.target_temp = 24
    v_t1.current_temp = 23
    v_t1.humidity = 45
    v_devs.append(v_t1)
    
    v_t2 = SmartThermostat("thermo2", "Bedroom Thermostat", "Bedroom")
    v_t2.target_temp = 22
    v_t2.current_temp = 28
    v_t2.humidity = 78
    v_devs.append(v_t2)
    
    v_c1 = SmartCamera("seccam1", "Front Door Camera", "Front Door")
    v_c1.battery_level = 25
    v_devs.append(v_c1)
    
    v_c2 = SmartCamera("seccam2", "Backyard Camera", "Backyard")
    v_c2.battery_level = 85
    v_c2._storage_used_mb = 30000
    v_devs.append(v_c2)
    
    v_w1 = SmartWaterMeter("water1", "Main Water Meter", "Utility Room")
    v_devs.append(v_w1)
    
    return v_devs


async def f_main(v_duration=30, v_speed=1.0):
    v_storage = StorageWorker("history.log")
    v_storage.start()
    v_stats = StorageStats(v_storage)
    
    v_devices = f_make_devices()
    print(f"\nCreated {len(v_devices)} devices:")
    for v_d in v_devices:
        print(f"  - {v_d.name} ({v_d.device_type}) @ {v_d.location}")
    
    v_ctrl = NetworkController(devices=v_devices, storage=v_storage, speed=v_speed)
    await v_ctrl.connect_all()
    
    print(f"Monitoring for {v_duration}s (speed: {v_speed}x)...\n")
    
    try:
        await v_ctrl.start(v_duration=v_duration)
    except KeyboardInterrupt:
        print("\nInterrupted")
        await v_ctrl.stop()
    
    v_readings = v_ctrl.get_readings()
    if v_readings:
        v_res = f_process_updates(v_readings)
        f_print_report(v_ctrl, v_res, v_stats)
    
    v_storage.stop()


def f_run():
    v_parser = argparse.ArgumentParser(description="EcoHub IoT Simulator")
    v_parser.add_argument("--runtime", type=float, default=30, help="Runtime in seconds (default: 30)")
    v_parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (default: 1.0)")
    v_args = v_parser.parse_args()
    
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    try:
        asyncio.run(f_main(v_args.runtime, v_args.speed))
    except KeyboardInterrupt:
        print("\nDone")


if __name__ == "__main__":
    f_run()
