# Fault Mode Grounding

The problem statement names 8 fault modes. This table states plainly,
for the pitch and the report, which are grounded in a real document and
which are our own construction. This table should be shown to judges
directly rather than discovered by them.

| Fault mode                        | Status in this project             | Grounding                                                                 |
|------------------------------------|--------------------------------------|------------------------------------------------------------------------------|
| Oil pressure / lubrication fault   | **Implemented, manual-grounded**    | Rotax 912 Series Operator's Manual, Chapter 4.4 'Oil pressure/Fuel pressure' (4.4.1 Oil pressure below minimum, 4.4.2 Oil pressure above permitted range at low ambient temperatures)      |
| Misfire / ignition fault           | **Implemented, manual-grounded**    | Rotax manual ignition check (300 rpm max single-circuit drop)              |
| Combustion instability             | **Implemented, partially grounded** | Carburetor icing is a well-documented general aviation piston engine phenomenon but is not covered in this specific Rotax 912 manual's abnormal-operation chapter; the fault model is based on general published carburetor-icing behavior (power/EGT drop, mixture enrichment) |
| Sensor drift                       | **Implemented, synthetic**          | No manufacturer analog — explicitly stated as synthetic                     |
| Injector abnormality               | Planned                             | To be grounded via fuel pressure limits (0.15–0.4 bar) + fuel consumption deviation |
| Alternator / electrical fault      | **Implemented, manual-grounded**    | Rotax 912 Series Operator's Manual, Chapter 7.4 'Electric system' (System Description chapter)          |
| Overheating / cooling fault        | **Implemented, manual-grounded**    | Rotax 912 Series Operator's Manual, Chapter 4.3 'Temperature' (4.3.1 Exceeding max. admissible cooling system temperature, 4.3.2 Exceeding max. admissible cylinder head temperature, 4.3.4 Exceeding max. admissible oil temperature)  |
| Injection timing fault             | Planned                             | Approximated only — real ECU maps are proprietary; will be stated as a limitation |

## How to talk about this in the pitch

"7 of our 8 fault modes are grounded in the Rotax 912 manufacturer's own
documented abnormal-operation and ignition-check procedures — a real
engine family used in fielded UAV platforms. Only sensor drift has no
manufacturer analog and is explicitly synthetic, which we state
directly rather than blend in unlabeled."

## Updating this table

Whenever a new fault mode is implemented in `engine_simulation/engine_simulator.py`,
update its row here immediately, including the specific manual section
or paper it draws from. Do not implement a fault mode without deciding
its grounding first — this table is what turns a "made up" simulator
into a defensible one.
