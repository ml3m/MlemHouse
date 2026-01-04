from devices import SmartBulb, SmartThermostat, SmartCamera, SmartFaucet
import asyncio
import threading
import queue
import time
import random
import sys
import argparse
from functools import reduce


v_data_queue = queue.Queue()
v_updates_buffer = []
v_running = True


def f_log(msg):
    print(msg)
    sys.stdout.flush()

def f_storage_worker():
    f_log("Storage Thread Started...")
    v_file = open("history.log", "a")
    while v_running:
        try:
            v_record = v_data_queue.get(timeout=0.5)
            v_file.write(str(v_record) + "\n")
            v_file.flush()
            v_data_queue.task_done()
        except queue.Empty:
            pass
    v_file.close()

def f_to_event(v_raw):
    return (v_raw["device_id"], v_raw["timestamp"], v_raw["payload"])

def f_is_critical(v_evt):
    v_payload = v_evt[2]
    v_temp = v_payload.get("current_temp")
    v_batt = v_payload.get("battery_level")
    return (v_temp is not None and v_temp > 30) or \
           (v_batt is not None and v_batt < 10) or \
           v_payload.get("motion_detected", False)

def f_sum_temps(v_acc, v_evt):
    v_temp = v_evt[2].get("current_temp")
    if v_temp is not None:
        v_acc["sum"] += v_temp
        v_acc["cnt"] += 1
    return v_acc

def f_sum_energy(v_acc, v_evt):
    v_kwh = v_evt[2].get("kwh", 0)
    if v_kwh:
        v_acc += v_kwh
    return v_acc

def f_process_batch(v_updates):
    v_evts = list(map(f_to_event, v_updates))
    v_critical = list(filter(f_is_critical, v_evts))
    v_temp_result = reduce(f_sum_temps, v_evts, {"sum": 0.0, "cnt": 0})
    v_total_energy = reduce(f_sum_energy, v_evts, 0.0)
    
    return {
        "total": len(v_evts),
        "critical_count": len(v_critical),
        "avg_temp": v_temp_result["sum"] / v_temp_result["cnt"] if v_temp_result["cnt"] else 0.0,
        "total_kwh": round(v_total_energy, 4)
    }

async def f_device_loop(v_dev, v_speed=1.0):
    global v_updates_buffer
    while True:
        if not v_dev.is_connected:
            await asyncio.sleep(1 / v_speed)
            continue
            
        v_upd = v_dev.send_update()
        v_data_queue.put(v_upd)
        v_updates_buffer.append(v_upd)
        
        v_pl = v_upd["payload"]
        v_dev_type = v_upd["type"]
        v_dev_id = v_upd["device_id"]
        
        if v_dev_type == "BULB":
            v_status = "ON" if v_pl.get("is_on") else "OFF"
            f_log(f"[{v_dev_id}] {v_status}, {v_pl.get('brightness')}% | {v_pl.get('kwh', 0):.4f}kWh")
        
        elif v_dev_type == "THERMOSTAT":
            f_log(f"[{v_dev_id}] temp={v_pl['current_temp']:.1f}C target={v_pl['target_temp']:.1f}C humid={v_pl['humidity']:.0f}% | {v_pl.get('kwh', 0):.4f}kWh")
            if v_pl.get("current_temp", 0) > 30:
                f_log("!! ALERT: High Temp detected! Triggering cooling...")
                try:
                    f_log(v_dev.execute_command("cool"))
                except:
                    pass
        
        elif v_dev_type == "CAMERA":
            v_motion = "MOTION" if v_pl.get("motion_detected") else "-"
            f_log(f"[{v_dev_id}] batt:{v_pl['battery_level']:.0f}% {v_motion} | recs:{v_pl.get('recordings', 0)}")
            if v_pl.get("battery_level", 100) < 10:
                f_log(f"!! ALERT: Low battery on {v_dev.name}")
            if v_pl.get("motion_detected"):
                f_log(f"!! Motion @ {v_dev.name}")
        
        elif v_dev_type == "FAUCET":
            v_flow = "FLOWING" if v_pl.get("flowing") else "OFF"
            f_log(f"[{v_dev_id}] {v_flow} ({v_pl.get('temp', 'warm')}) | {v_pl.get('liters', 0):.2f}L")
        
        await asyncio.sleep(random.uniform(1, 3) / v_speed)

async def f_connect_all(v_devices):
    f_log("Connecting devices...")
    await asyncio.gather(*[d.connect() for d in v_devices])
    f_log("All devices connected!")

async def f_run_main(v_devices, v_duration, v_speed=1.0):
    await f_connect_all(v_devices)
    
    v_tasks = [asyncio.create_task(f_device_loop(d, v_speed)) for d in v_devices]
    
    f_log(f"\nRunning for {v_duration}s (speed: {v_speed}x)...")
    f_log("-" * 40)
    
    await asyncio.sleep(v_duration)
    
    for t in v_tasks:
        t.cancel()
    
    try:
        await asyncio.gather(*v_tasks)
    except:
        pass

def f_main():
    global v_running, v_updates_buffer
    
    v_parser = argparse.ArgumentParser(description="EcoHub IoT Device Simulator")
    v_parser.add_argument("--runtime", type=int, default=20, help="Runtime in seconds (default: 20)")
    v_parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (default: 1.0, higher=faster)")
    v_args = v_parser.parse_args()
    
    v_thread = threading.Thread(target=f_storage_worker, daemon=True)
    v_thread.start()
    
    v_devices = [
        SmartBulb("bulb1", "Living Room Light", "Living Room"),
        SmartThermostat("thermo1", "Bedroom Thermostat", "Bedroom"),
        SmartCamera("seccam1", "Front Door Cam", "Front Door"),
        SmartFaucet("faucet1", "Kitchen Faucet", "Kitchen"),
    ]
    
    try:
        asyncio.run(f_run_main(v_devices, v_args.runtime, v_args.speed))
    except KeyboardInterrupt:
        f_log("\nStopped.")
    
    f_log("\n" + "-" * 40)
    
    if v_updates_buffer:
        v_stats = f_process_batch(v_updates_buffer)
        f_log("Analytics Summary (Functional Pipeline):")
        f_log(f"  Total updates: {v_stats['total']}")
        f_log(f"  Critical events: {v_stats['critical_count']}")
        f_log(f"  Avg temperature: {v_stats['avg_temp']:.1f}C")
        f_log(f"  Total energy: {v_stats['total_kwh']} kWh")
    
    f_log("-" * 40)
    f_log("Flushing storage...")
    v_data_queue.join()
    v_running = False
    f_log("Done.")


if __name__ == "__main__":
    f_main()
