# Data Contract

This is the schema shared between `engine_simulation/` (producer) and
`ai_layer/` + `dashboard/` (consumers). Any change to this schema must
be agreed by both team members and updated here first.

## Record schema

Each telemetry record (one row of CSV / one JSON object) contains:

| Field                  | Type   | Unit    | Description                                              | Source in Rotax manual |
|-------------------------|--------|---------|-----------------------------------------------------------|--------------------------|
| `timestamp`             | float  | seconds | Time since mission start                                   | —                        |
| `rpm`                   | float  | rpm     | Engine rotational speed                                    | Operating limits table |
| `cht_c`                 | float  | °C      | Cylinder head temperature                                   | Operating limits table |
| `egt_c`                 | float  | °C      | Exhaust gas temperature                                     | Operating limits table |
| `oil_pressure_bar`      | float  | bar     | Oil pressure                                                | Operating limits table |
| `oil_temp_c`            | float  | °C      | Oil temperature                                              | Operating limits table |
| `fuel_flow_lph`         | float  | L/h     | Fuel flow rate                                               | Performance table       |
| `vibration_g`           | float  | g       | Vibration amplitude (synthetic; no manual reference)         | Synthetic               |
| `alternator_v`          | float  | V       | Alternator/charging voltage                                  | Electrical system chapter |
| `injection_timing_deg`  | float  | °BTDC   | Ignition/injection timing setpoint (simplified; ECU maps proprietary) | Approximated |
| `altitude_m`            | float  | m       | Mission altitude                                             | —                        |
| `fault_label`           | string | —       | `"none"` or one of the fault-mode keys below                 | —                        |
| `fault_cylinder`        | int    | —       | (Only present during misfire fault) affected cylinder number | —                        |

## Fault label values

- `"none"`
- `"oil_pressure_fault"`
- `"misfire_fault"`
- `"sensor_drift_fault"`

See `fault_grounding.md` for what each represents and how it was derived.

## Rules for anyone consuming this data

1. Treat `engine_simulation/engine_simulator.py`'s `steady_state_engine()`
   function as the single source of truth for "expected/healthy" values.
   Do not re-derive expected values independently in the AI layer —
   import and reuse this function so the residual comparison stays
   consistent.
2. Any new field added to a record must be added to this table first.
3. Units are fixed as listed above — do not silently convert (e.g. do
   not switch oil pressure to PSI in one module without updating this
   file and the other module).
