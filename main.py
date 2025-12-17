#!/usr/bin/env python3
"""ecohub main"""

import asyncio
import argparse
import signal
import sys

from devices import SmartDevice, SmartBulb, SmartThermostat, SmartCamera
from storage import StorageWorker, StorageStats
from network import NetworkController
from analytics import process_updates
from utils import print_report


def make_devices():
    devs = []
    
    b1 = SmartBulb("bulb_01", "Mysterious Smart Bulb", "Living Room")
    b1.brightness = 100
    b1.is_on = False
    devs.append(b1)
    
    b2 = SmartBulb("bulb_02", "Ambient Smart Bulb", "Bedroom")
    b2.brightness = 50
    b2.is_on = True
    devs.append(b2)
    
    t1 = SmartThermostat("thermo_01", "Famous Smart Thermostat", "Living Room")
    t1.target_temp = 24
    t1.current_temp = 23
    t1.humidity = 45
    devs.append(t1)
    
    t2 = SmartThermostat("thermo_02", "Cozy Smart Thermostat", "Bedroom")
    t2.target_temp = 22
    t2.current_temp = 28
    t2.humidity = 78
    devs.append(t2)
    
    c1 = SmartCamera("cam_01", "Gorgeous Smart Camera", "Front Door")
    c1.battery_level = 25
    devs.append(c1)
    
    c2 = SmartCamera("cam_02", "Vigilant Smart Camera", "Backyard")
    c2.battery_level = 85
    c2._storage_used_mb = 30000
    devs.append(c2)
    
    return devs




async def main(duration=30):
    storage = StorageWorker("history.log")
    storage.start()
    stats = StorageStats(storage)
    
    devices = make_devices()
    print(f"\nCreated {len(devices)} devices:")
    for d in devices:
        print(f"  - {d.name} ({d.device_type}) @ {d.location}")
    
    ctrl = NetworkController(devices=devices, storage=storage)
    await ctrl.connect_all()
    
    print(f"Monitoring for {duration}s...\n")
    
    try:
        await ctrl.start(duration=duration)
    except KeyboardInterrupt:
        print("\nInterrupted")
        await ctrl.stop()
    
    readings = ctrl.get_readings()
    if readings:
        res = process_updates(readings)
        print_report(ctrl, res, stats)
    
    storage.stop()


def run():
    parser = argparse.ArgumentParser(description="EcoHub IoT sim")
    parser.add_argument("-d", "--duration", type=float, default=30, help="seconds to run")
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    try:
        asyncio.run(main(args.duration))
    except KeyboardInterrupt:
        print("\nDone")


if __name__ == "__main__":
    run()
