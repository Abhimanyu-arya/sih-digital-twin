# Rotax 912 Series — Calibration Notes

**Source (official manufacturer document):**
https://avsport.org/acft/Rotax/OM_912_Series_ED4_R0.pdf
(mirror: https://www.rotax-owner.com/pdf/OM_912_Series_ED4_R0.pdf)

Rotax 912-series engines are a real engine family used in multiple
fielded UAV platforms, not just general aviation aircraft, which is why
this manual is a defensible calibration source for an aero-UAV piston
engine digital twin even though it is not an internal DRDO/manufacturer
document.

## Operating limits used in `engine_simulator.py`

| Parameter          | Value                                            |
|---------------------|---------------------------------------------------|
| Idle RPM            | 1,400 min                                          |
| Max continuous RPM  | 5,500                                               |
| Takeoff RPM         | 5,800 (max 5 minutes)                               |
| Oil pressure        | Min 0.8 bar / Normal 2.0–5.0 bar / Max 7 bar        |
| Oil temperature     | Normal 90–110 °C / Max 130–140 °C (variant-dependent) |
| EGT                 | Max 880 °C                                          |
| Cylinder head temp  | Max 135–150 °C (variant-dependent)                  |
| Fuel pressure       | 0.15–0.4 bar                                        |
| Fuel consumption    | ~16–27 L/h depending on power setting               |

## Performance table (power setting → rpm → fuel flow → manifold pressure)

Used to calibrate `POWER_TABLE` in `engine_simulator.py`:

| Power setting     | RPM   | Power (kW) | Fuel flow (L/h) | Manifold pressure (inHg) |
|-------------------|-------|------------|-------------------|-----------------------------|
| 55%               | 4,300 | 38.0       | 18.5              | 24.0                        |
| 65%               | 4,800 | 44.6       | 18.5              | 26.0                        |
| 75%               | 5,000 | 51.0       | 18.5              | 26.0                        |
| Max continuous    | 5,500 | 69.0       | 25.0              | 27.0                        |
| Takeoff (5 min)   | 5,800 | 73.5       | 27.0              | 27.5                        |

## Abnormal-operation guidance used for fault grounding

The manual's abnormal-operation and troubleshooting chapters document
real cause → symptom relationships, including:

- Low oil pressure ↔ insufficient oil / overheated oil
- High oil pressure ↔ cold oil / wrong viscosity
- CHT/coolant temperature exceedance ↔ requires pilot action, logged event
- Knocking under load ↔ low octane fuel
- Rough idle + smoky exhaust after warm-up ↔ choke left engaged
- Hard cold starts ↔ battery charge / oil viscosity / preheat issues
- Carburetor icing ↔ humidity + throttle position; performance loss and
  mixture change

## Ignition check reference (used for misfire fault calibration)

The manual's ignition check procedure specifies a maximum allowed speed
drop of **300 rpm** when running on a single ignition circuit
(single-magneto check). This figure is used as the reference severity
scale for the `misfire_fault` injection in `engine_simulator.py`.

## What this manual does NOT give us

- Exact proprietary ECU/fuel-injection maps (injection timing curve used
  in the simulator is a simplified approximation, not the real map)
- Vibration signatures (no vibration data in the manual; vibration
  behaviour is synthetic)
- Sensor drift behaviour (no manufacturer analog; purely synthetic)
- Any labeled fault time-series data — the manual gives static
  cause/effect descriptions, not sensor traces, so the actual injected
  fault *trajectories* in code are still our own construction, just
  constrained to match the manual's described end-states and thresholds.
