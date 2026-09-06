# Fault Mode Grounding

The problem statement names 8 fault modes. This table states plainly,
for the pitch and the report, which are grounded in a real document and
which are our own construction. This table should be shown to judges
directly rather than discovered by them.

| Fault mode                        | Status in this project             | Grounding                                                                 |
|------------------------------------|--------------------------------------|------------------------------------------------------------------------------|
| Oil pressure / lubrication fault   | **Implemented, manual-grounded**    | Rotax manual abnormal-operation section (low/high oil pressure causes)      |
| Misfire / ignition fault           | **Implemented, manual-grounded**    | Rotax manual ignition check (300 rpm max single-circuit drop)              |
| Combustion instability             | Planned                             | To be grounded via carburetor icing section (documented performance/mixture change) |
| Sensor drift                       | **Implemented, synthetic**          | No manufacturer analog — explicitly stated as synthetic                     |
| Injector abnormality               | Planned                             | To be grounded via fuel pressure limits (0.15–0.4 bar) + fuel consumption deviation |
| Alternator / electrical fault      | Planned                             | To be grounded via electrical system chapter charging description          |
| Overheating / cooling fault        | Planned                             | To be grounded via CHT/coolant exceedance sections and real max thresholds  |
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
