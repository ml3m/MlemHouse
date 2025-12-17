"""
MlemHouse Configuration - Romanian Utility Rates (Timișoara)
"""

# ============================================================================
# Utility Rates - Romania / Timișoara
# ============================================================================

UTILITY_RATES = {
    # Electricity rates (lei/kWh)
    "electricity": {
        "rate_low": 1.06,       # Night/off-peak
        "rate_high": 1.13,      # Day/peak
        "rate_avg": 1.10,       # Average used for estimates
        "currency": "lei",
        "unit": "kWh"
    },
    
    # Gas rates (lei/kWh) - for heating
    "gas": {
        "rate": 0.31,
        "currency": "lei", 
        "unit": "kWh",
        # Typical gas boiler efficiency
        "boiler_efficiency": 0.92  # 92% efficiency
    },
    
    # Water rates (lei/m³)
    "water": {
        "rate": 7.71,
        "currency": "lei",
        "unit": "m³",
        # Sewage is typically charged alongside water
        "sewage_rate": 4.50,  # Approximate sewage rate
        "total_rate": 12.21   # Water + sewage combined
    }
}

# Currency settings
CURRENCY = {
    "code": "RON",
    "symbol": "lei",
    "symbol_position": "after",  # 10.50 lei (not lei 10.50)
    "decimal_places": 2
}

# ============================================================================
# Energy Consumption Estimates (Watts/kWh)
# These are DEFAULT values - devices can have custom values
# ============================================================================

DEVICE_ENERGY = {
    # Smart bulbs (LED) - typical range 5W-15W
    "BULB": {
        "max_watts": 10,           # 10W LED bulb (default)
        "standby_watts": 0.5,      # WiFi standby
        "min_watts": 1,            # Minimum configurable
        "configurable_max": 100,   # Maximum configurable (for incandescent simulation)
    },
    
    # Thermostat (controls HVAC, doesn't consume much itself)
    "THERMOSTAT": {
        "device_watts": 3,         # The thermostat device itself
        # Gas heating consumption (when heating is active)
        "heating_kwh_per_degree": 0.8,  # kWh of gas per degree difference per hour
        # Cooling (AC) consumption
        "cooling_watts": 2500,     # Typical AC unit
    },
    
    # Camera
    "CAMERA": {
        "active_watts": 5,
        "standby_watts": 2,
        "recording_watts": 8
    },
    
    # Water meter (minimal)
    "WATER_METER": {
        "active_watts": 1,
        "standby_watts": 0.5
    }
}

# ============================================================================
# Time Simulation Settings
# ============================================================================

TIME_SIMULATION = {
    "multipliers": [1, 10, 60, 360, 1440],  # 1x, 10x, 1min=1sec, 1hr=10sec, 1day=1min
    "labels": ["Real-time", "10x", "1 min/sec", "1 hr/10sec", "1 day/min"],
    "default": 1
}

# ============================================================================
# Heating Calculation Parameters
# ============================================================================

HEATING_CONFIG = {
    # Outside temperature simulation for Timișoara
    "outside_temp_winter": 2,      # Average winter temp
    "outside_temp_summer": 28,     # Average summer temp
    "outside_temp_current": 5,     # Current season estimate
    
    # House thermal properties (simplified)
    "heat_loss_coefficient": 0.15,  # kW per degree difference
    
    # Gas boiler specs
    "boiler_power_kw": 24,         # Typical 24kW gas boiler
    "boiler_efficiency": 0.92,
}

# ============================================================================
# Carbon Footprint (kg CO2 per kWh)
# ============================================================================

CARBON_FOOTPRINT = {
    "electricity": 0.3,    # Romania grid average (mix of sources)
    "gas": 0.2,            # Natural gas combustion
    "water": 0.001         # Water treatment/pumping per liter
}

# ============================================================================
# Helper Functions
# ============================================================================

def format_currency(amount: float) -> str:
    """Format amount with Romanian lei"""
    return f"{amount:.2f} {CURRENCY['symbol']}"

def calculate_electricity_cost(kwh: float) -> float:
    """Calculate electricity cost in lei"""
    return kwh * UTILITY_RATES["electricity"]["rate_avg"]

def calculate_gas_cost(kwh: float) -> float:
    """Calculate gas cost in lei"""
    return kwh * UTILITY_RATES["gas"]["rate"]

def calculate_water_cost(liters: float) -> float:
    """Calculate water cost in lei (including sewage)"""
    cubic_meters = liters / 1000
    return cubic_meters * UTILITY_RATES["water"]["total_rate"]

def liters_to_cubic_meters(liters: float) -> float:
    """Convert liters to cubic meters"""
    return liters / 1000
