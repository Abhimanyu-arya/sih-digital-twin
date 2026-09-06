"""
engine_simulator.py

Physics-informed digital-twin data generator for a Rotax 912 ULS-class
aero piston engine (representative of engines used in MALE UAVs).

WHY THIS EXISTS
----------------
No public real-world telemetry or run-to-failure dataset exists for aero
piston engines. Instead of inventing arbitrary numbers, every constant and
curve in this file is calibrated against the official Rotax 912 Series
Operator's Manual (BRP-Rotax, Edition 4 / Rev. 0, Nov 2016):

    https://avsport.org/acft/Rotax/OM_912_Series_ED4_R0.pdf

Specifically grounded in that document:
  - RPM range (idle / max continuous / takeoff)
  - Power / torque / manifold pressure / fuel consumption table
    (55%, 65%, 75%, max-continuous, take-off power settings)
  - Oil pressure and oil temperature operating limits
  - EGT and CHT operating limits
  - Ignition check procedure: max 300 rpm speed drop when running on a
    single ignition circuit (Chapter 3.5) -> used to calibrate the
    misfire/ignition fault signature below.

WHAT IS *NOT* GROUNDED (and you should say so explicitly in your report):
  - Sensor drift fault (no manufacturer analog exists; purely synthetic)
  - Exact noise statistics (approximate, not measured from a real sensor)
  - Any transient/dynamic combustion physics inside a single cycle
    (this is a mean-value model, not a crank-angle-resolved model)

DATA CONTRACT (matches the schema agreed on for the AI/dashboard side)
------------------------------------------------------------------------
Each emitted record is a dict with keys:
    timestamp, rpm, cht_c, egt_c, oil_pressure_bar, oil_temp_c,
    fuel_flow_lph, vibration_g, alternator_v, injection_timing_deg,
    altitude_m, fault_label
"""

import json
import math
import random
import csv
from dataclasses import dataclass, asdict


# ---------------------------------------------------------------------
# 1. CALIBRATION DATA (from the Rotax 912 ULS operating limits & table)
# ---------------------------------------------------------------------

# Power-setting table: (rpm, power_kw, fuel_flow_lph, manifold_pressure_inHg)
# Values taken from the 912 S/ULS performance table in the manual.
POWER_TABLE = [
    (4300, 38.0, 18.5, 24.0),   # 55% power
    (4800, 44.6, 18.5, 26.0),   # 65% power (fuel flow interpolated near 65%)
    (5000, 51.0, 18.5, 26.0),   # 75% power
    (5500, 69.0, 25.0, 27.0),   # max continuous
    (5800, 73.5, 27.0, 27.5),   # take-off (max 5 min)
]

RPM_IDLE = 1400
RPM_MAX_CONTINUOUS = 5500
RPM_TAKEOFF = 5800  # max 5 minutes

OIL_PRESSURE_NORMAL_BAR = (2.0, 5.0)   # above 3500 rpm
OIL_PRESSURE_MIN_BAR = 0.8
OIL_PRESSURE_MAX_BAR = 7.0

OIL_TEMP_NORMAL_C = (90, 110)
OIL_TEMP_MAX_C = 130

EGT_MAX_C = 880
CHT_MAX_C = 135
CHT_NORMAL_CRUISE_C = 120   # typical cruise value, safely under the 135 max

FUEL_PRESSURE_BAR = (0.15, 0.4)

ALTERNATOR_NOMINAL_V = 13.8  # typical light aircraft/UAV 12V-system charging voltage


# ---------------------------------------------------------------------
# 2. MEAN-VALUE ENGINE MODEL (steady-state relationships)
# ---------------------------------------------------------------------

def interpolate_power_table(rpm):
    """Linearly interpolate (fuel_flow, manifold_pressure, power_kw) for a given rpm
    using the manufacturer's performance table as calibration anchor points."""
    table = POWER_TABLE
    if rpm <= table[0][0]:
        return table[0][1:]
    if rpm >= table[-1][0]:
        return table[-1][1:]
    for i in range(len(table) - 1):
        r0, p0, f0, m0 = table[i]
        r1, p1, f1, m1 = table[i + 1]
        if r0 <= rpm <= r1:
            frac = (rpm - r0) / (r1 - r0)
            power = p0 + frac * (p1 - p0)
            fuel = f0 + frac * (f1 - f0)
            map_ = m0 + frac * (m1 - m0)
            return power, fuel, map_
    return table[-1][1:]


def altitude_density_factor(altitude_m):
    """Simplified ISA-like air density falloff used to derate combustion
    efficiency at altitude (thinner air -> lower EGT/CHT rise per unit fuel,
    lower effective power for a given throttle position)."""
    return math.exp(-altitude_m / 8500.0)  # 8500 m ~ atmospheric scale height


def steady_state_engine(rpm, altitude_m=0.0, oat_c=15.0):
    """Compute the engine's 'should be' sensor values for a given RPM,
    altitude and outside air temperature. This is the physics-informed
    baseline that the AI layer compares live/simulated 'sensor' data against
    (the residual-based approach)."""

    power_kw, fuel_flow_lph, map_inhg = interpolate_power_table(rpm)
    density = altitude_density_factor(altitude_m)

    # Combustion efficiency drops with altitude -> less fuel actually burned
    # effectively per unit time at a fixed throttle position.
    effective_fuel_flow = fuel_flow_lph * (0.4 + 0.6 * density)

    # EGT rises with fuel flow / load, capped near the manual's max operating band.
    load_fraction = (rpm - RPM_IDLE) / (RPM_TAKEOFF - RPM_IDLE)
    load_fraction = max(0.0, min(1.0, load_fraction))
    egt_c = 550 + load_fraction * 300 * (0.85 + 0.15 * density)  # normal cruise ~700-800C, redline 880C

    # CHT rises with load and ambient temperature, cooled somewhat by higher airspeed
    # at higher RPM (approximate; not a full heat-transfer model).
    cht_c = 90 + load_fraction * 40 + 0.15 * (oat_c - 15)
    cht_c = min(cht_c, CHT_MAX_C - 5)  # keep healthy engine comfortably under redline

    # Oil pressure: roughly flat above 3500 rpm per the manual's normal band,
    # lower and more variable below that.
    if rpm >= 3500:
        oil_pressure_bar = 3.5 - 0.1 * load_fraction
    else:
        oil_pressure_bar = 1.5 + (rpm / 3500) * 2.0

    # Oil temperature climbs slowly toward the normal band with load/time;
    # steady-state approximation here (a full model would use a thermal lag).
    oil_temp_c = 95 + load_fraction * 12

    # Alternator output assumed nominal/healthy at steady state.
    alternator_v = ALTERNATOR_NOMINAL_V

    # Injection/ignition timing setpoint (degrees BTDC) - simplified constant
    # schedule vs RPM, since exact Rotax ECU maps are proprietary.
    injection_timing_deg = 5 + 20 * load_fraction

    # Vibration baseline in g, low at steady healthy running.
    vibration_g = 0.05 + 0.02 * load_fraction

    return {
        "rpm": rpm,
        "cht_c": cht_c,
        "egt_c": egt_c,
        "oil_pressure_bar": oil_pressure_bar,
        "oil_temp_c": oil_temp_c,
        "fuel_flow_lph": effective_fuel_flow,
        "vibration_g": vibration_g,
        "alternator_v": alternator_v,
        "injection_timing_deg": injection_timing_deg,
        "altitude_m": altitude_m,
    }


# ---------------------------------------------------------------------
# 3. FAULT INJECTION (each grounded in the manual's abnormal-operation
#    chapter, except sensor_drift which is explicitly synthetic)
# ---------------------------------------------------------------------

def inject_oil_pressure_fault(state, progress):
    """Lubrication-system fault: gradual oil pressure loss with a compensatory
    rise in oil temperature, consistent with the manual's 'oil pressure below
    minimum' abnormal-operation guidance (Chapter 4.4 'Oil pressure/Fuel pressure' (4.4.1 Oil pressure below minimum, 4.4.2 Oil pressure above permitted range at low ambient temperatures)). `progress` in [0, 1]
    represents how far into the developing fault we are."""
    state = dict(state)
    pressure_loss = progress * 4.0          # bar, drifting toward/below the 0.8 bar minimum
    state["oil_pressure_bar"] = max(0.3, state["oil_pressure_bar"] - pressure_loss)
    state["oil_temp_c"] += progress * 20     # friction/heat rises as lubrication degrades
    state["vibration_g"] += progress * 0.05  # increased mechanical wear noise
    return state


def inject_misfire_fault(state, progress, cylinder=2):
    """Ignition/misfire fault on one cylinder. Calibrated against the manual's
    documented ignition check: switching to a single ignition circuit causes
    up to a 300 rpm drop (Chapter 3.5). We scale a partial-misfire severity
    off that reference figure, plus the expected EGT/vibration signature of
    a dead or weak cylinder (unburned fuel exits hotter/cooler depending on
    misfire type; here modeled as a cooling of the affected cylinder's EGT
    and a rise in vibration from the resulting imbalance).
    Note: At full progress, this exceeds the Rotax manual's 300 rpm reference
    figure because it models progression to actual failure, not just the
    ignition-check scenario."""
    state = dict(state)
    max_rpm_drop_ref = 300  # from the manual's ignition check limit
    state["rpm"] -= progress * max_rpm_drop_ref * 1.2
    state["egt_c"] -= progress * 120   # affected cylinder runs cooler (incomplete combustion)
    state["vibration_g"] += progress * 0.12  # firing imbalance -> vibration signature
    state["fault_cylinder"] = cylinder
    return state


def inject_sensor_drift_fault(state, progress, channel="oil_pressure_bar"):
    """NOT grounded in any manufacturer document - purely synthetic, and this
    should be stated explicitly in your report. Simulates a slowly drifting
    (biased) sensor reading, independent of the engine's true physical state."""
    state = dict(state)
    state[channel] = state[channel] * (1 + 0.15 * progress)
    return state


def inject_combustion_instability_fault(state, progress):
    """Combustion instability fault (carburetor icing). This model is based on
    general aviation piston-engine carburetor icing behavior (gradual power and EGT drop, richer mixture leading to increased fuel flow, and increased RPM variance). Not directly grounded in the Rotax 912 manual.
    `progress` in [0, 1] indicates fault development.
    """
    state = dict(state)
    # Power and EGT drop
    state["egt_c"] -= progress * 200  # gradual EGT decrease
    # Fuel flow increase due to richer mixture
    state["fuel_flow_lph"] += progress * 2.0
    # Increase RPM variance (add zero-mean noise)
    state["rpm"] += random.gauss(0, 10 * progress)
    return state

def inject_overheating_fault(state, progress):
    """Overheating fault: gradual increase in cylinder head temperature (CHT) and oil temperature.
    Grounded in Rotax 912 Series Operator's Manual, Chapter 4.3 'Temperature' (specifically 4.3.1 Exceeding max. admissible cooling system temperature, 4.3.2 Exceeding max. admissible cylinder head temperature, 4.3.4 Exceeding max. admissible oil temperature).
    `progress` in [0, 1] indicates fault development.
    """
    state = dict(state)
    # Increase CHT and oil temperature proportionally
    state["cht_c"] += progress * 30  # approach/exceed max thresholds
    state["oil_temp_c"] += progress * 25
    return state

def inject_alternator_fault(state, progress):
    """Alternator/electrical fault: gradual drop in alternator voltage.
    Grounded in Rotax 912 Series Operator's Manual, Chapter 7.4 'Electric system' (System Description chapter).
    `progress` in [0, 1] indicates fault development.
    """
    state = dict(state)
    # Voltage drop up to ~3V reduction
    state["alternator_v"] = max(10.0, state["alternator_v"] - progress * 3.0)
    return state

FAULT_FUNCTIONS = {
    "oil_pressure_fault": inject_oil_pressure_fault,
    "misfire_fault": inject_misfire_fault,
    "sensor_drift_fault": inject_sensor_drift_fault,
    "combustion_instability_fault": inject_combustion_instability_fault,
    "overheating_fault": inject_overheating_fault,
    "alternator_fault": inject_alternator_fault,
}


# ---------------------------------------------------------------------
# 4. SENSOR NOISE (real sensors are noisy; makes downstream anomaly
#    detection train/test on something more honest than clean numbers)
# ---------------------------------------------------------------------

NOISE_STD = {
    "rpm": 8.0,
    "cht_c": 1.5,
    "egt_c": 4.0,
    "oil_pressure_bar": 0.05,
    "oil_temp_c": 0.8,
    "fuel_flow_lph": 0.3,
    "vibration_g": 0.01,
    "alternator_v": 0.1,
    "injection_timing_deg": 0.3,
}


def add_noise(state):
    noisy = dict(state)
    for key, std in NOISE_STD.items():
        if key in noisy:
            noisy[key] = noisy[key] + random.gauss(0, std)
    return noisy


# ---------------------------------------------------------------------
# 5. MISSION SIMULATION LOOP
# ---------------------------------------------------------------------

def simulate_mission(duration_s=1800, sample_rate_hz=1.0, cruise_rpm=5000,
                      altitude_m=1500.0, fault_type=None, fault_start_s=None,
                      fault_ramp_s=300):
    """Generate a full mission's worth of telemetry records.

    fault_type: one of FAULT_FUNCTIONS keys, or None for a healthy flight.
    fault_start_s: time (s) the fault begins developing.
    fault_ramp_s: time (s) over which the fault progresses from 0 -> 1 severity.
    """
    records = []
    n_samples = int(duration_s * sample_rate_hz)

    for i in range(n_samples):
        t = i / sample_rate_hz

        # Simple mission profile: climb, cruise, descent.
        if t < 120:
            rpm = RPM_IDLE + (cruise_rpm - RPM_IDLE) * (t / 120)
            alt = altitude_m * (t / 120)
        elif t > duration_s - 120:
            frac = (duration_s - t) / 120
            rpm = RPM_IDLE + (cruise_rpm - RPM_IDLE) * frac
            alt = altitude_m * frac
        else:
            rpm = cruise_rpm
            alt = altitude_m

        state = steady_state_engine(rpm, altitude_m=alt)
        state["commanded_rpm"] = rpm

        fault_label = "none"
        if fault_type and fault_start_s is not None and t >= fault_start_s:
            progress = min(1.0, (t - fault_start_s) / fault_ramp_s)
            state = FAULT_FUNCTIONS[fault_type](state, progress)
            fault_label = fault_type if progress > 0.05 else "none"

        state = add_noise(state)
        state["timestamp"] = round(t, 2)
        state["fault_label"] = fault_label
        records.append(state)

    return records


def simulate_mission_variable_profile(duration_s=1800, sample_rate_hz=1.0,
                                       cruise_rpm=5000, altitude_m=1500.0,
                                       rpm_schedule=None,
                                       fault_type=None, fault_start_s=None,
                                       fault_ramp_s=300):
    """Generate a mission with mid-cruise RPM step-changes (rapid throttle
    transitions), directly addressing the SIH problem statement's requirement.

    rpm_schedule: list of (start_time_s, target_rpm, ramp_s) tuples defining
        RPM changes during the cruise phase. Between transitions the engine
        holds the last commanded RPM. If None, behaves identically to
        simulate_mission (single cruise RPM, no transitions).
    """
    climb_s = 120.0
    descent_s = 120.0

    # Pre-compute the RPM timeline from the schedule.
    # Each entry: (t_start, t_end_of_ramp, from_rpm, to_rpm)
    transitions = []
    if rpm_schedule:
        for seg_start, seg_rpm, seg_ramp in sorted(rpm_schedule, key=lambda x: x[0]):
            transitions.append((seg_start, seg_start + seg_ramp, seg_rpm))

    def _get_cruise_rpm(t):
        """Resolve the commanded RPM at time `t` during the cruise phase,
        accounting for any scheduled transitions."""
        if not transitions:
            return cruise_rpm
        current_target = cruise_rpm
        for t_start, t_end, target in transitions:
            if t < t_start:
                break
            elif t <= t_end:
                # Mid-ramp: linearly interpolate
                prev_target = current_target
                frac = (t - t_start) / max(1.0, t_end - t_start)
                return prev_target + frac * (target - prev_target)
            else:
                current_target = target
        return current_target

    records = []
    n_samples = int(duration_s * sample_rate_hz)

    for i in range(n_samples):
        t = i / sample_rate_hz

        # Phase: climb, cruise (with transitions), descent
        if t < climb_s:
            target_rpm = _get_cruise_rpm(climb_s)  # climb toward first cruise rpm
            rpm = RPM_IDLE + (target_rpm - RPM_IDLE) * (t / climb_s)
            alt = altitude_m * (t / climb_s)
        elif t > duration_s - descent_s:
            frac = (duration_s - t) / descent_s
            target_rpm = _get_cruise_rpm(duration_s - descent_s)
            rpm = RPM_IDLE + (target_rpm - RPM_IDLE) * frac
            alt = altitude_m * frac
        else:
            rpm = _get_cruise_rpm(t)
            alt = altitude_m

        state = steady_state_engine(rpm, altitude_m=alt)
        state["commanded_rpm"] = rpm

        fault_label = "none"
        if fault_type and fault_start_s is not None and t >= fault_start_s:
            progress = min(1.0, (t - fault_start_s) / fault_ramp_s)
            state = FAULT_FUNCTIONS[fault_type](state, progress)
            fault_label = fault_type if progress > 0.05 else "none"

        state = add_noise(state)
        state["timestamp"] = round(t, 2)
        state["fault_label"] = fault_label
        records.append(state)

    return records


def save_records(records, path):
    if path.endswith(".json"):
        with open(path, "w") as f:
            json.dump(records, f, indent=2)
    elif path.endswith(".csv"):
        keys = sorted({k for r in records for k in r.keys()})
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in records:
                writer.writerow(r)


# ---------------------------------------------------------------------
# 6. DEMO: the exact "smallest thing that wins the room" scenario
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import os
    os.makedirs("engine_simulation/data", exist_ok=True)

    demos = [
        ("oil_pressure_fault",            600, 300),
        ("misfire_fault",                  800, 200),
        ("combustion_instability_fault",   600, 300),
        ("overheating_fault",              600, 600),
        ("alternator_fault",               600, 300),
    ]

    for fault_name, start_s, ramp_s in demos:
        mission = simulate_mission(
            duration_s=1800,
            sample_rate_hz=1.0,
            cruise_rpm=5000,
            altitude_m=2000,
            fault_type=fault_name,
            fault_start_s=start_s,
            fault_ramp_s=ramp_s,
        )
        tag = fault_name.replace("_fault", "")
        save_records(mission, f"engine_simulation/data/demo_mission_{tag}_fault.csv")
        save_records(mission, f"engine_simulation/data/demo_mission_{tag}_fault.json")
        print(f"[{fault_name}] Generated {len(mission)} records  "
              f"-> engine_simulation/data/demo_mission_{tag}_fault.{{csv,json}}")

    # Quick sanity print from the first mission
    first = simulate_mission(duration_s=1800, cruise_rpm=5000, altitude_m=2000,
                             fault_type="oil_pressure_fault", fault_start_s=600,
                             fault_ramp_s=300)
    print("\nSample healthy record (t=300s):", first[300])
    print("Sample faulted record (t=750s):", first[750])
