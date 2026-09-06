"""
test_engine_simulator.py

Unit tests for fault injection functions in engine_simulator.py.

Each test class verifies three properties:
  1. The fault function returns a dict with all original keys intact.
  2. At progress=0 the returned values are very close to the unfaulted baseline.
  3. At progress=1 the expected sensor channels deviate in the correct direction.
"""

import sys
import os
import unittest

# Ensure the project root is on sys.path so we can import engine_simulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine_simulation.engine_simulator import (
    steady_state_engine,
    inject_oil_pressure_fault,
    inject_misfire_fault,
    inject_sensor_drift_fault,
    inject_combustion_instability_fault,
    inject_overheating_fault,
    inject_alternator_fault,
)

# A reproducible baseline state at a typical cruise condition.
BASELINE_RPM = 5000
BASELINE_ALT = 1500.0
BASELINE = steady_state_engine(BASELINE_RPM, altitude_m=BASELINE_ALT)

# Helper: all keys that must survive every fault injection
REQUIRED_KEYS = set(BASELINE.keys())


class _FaultTestMixin:
    """Shared assertions reused by every fault-specific test class."""

    fault_fn = None  # override in subclass
    fault_kwargs = {}  # extra kwargs (e.g. cylinder=2)

    def _call(self, progress):
        return self.fault_fn(BASELINE, progress, **self.fault_kwargs)

    def test_keys_preserved(self):
        """Fault function must return all original keys."""
        result = self._call(0.5)
        self.assertTrue(
            REQUIRED_KEYS.issubset(result.keys()),
            f"Missing keys: {REQUIRED_KEYS - set(result.keys())}",
        )

    def test_progress_zero_near_baseline(self):
        """At progress=0, values should be very close to the unfaulted state."""
        result = self._call(0.0)
        for key in REQUIRED_KEYS:
            if isinstance(BASELINE[key], (int, float)):
                self.assertAlmostEqual(
                    result[key],
                    BASELINE[key],
                    places=4,
                    msg=f"{key} diverged at progress=0",
                )


class TestOilPressureFault(_FaultTestMixin, unittest.TestCase):
    fault_fn = staticmethod(inject_oil_pressure_fault)

    def test_pressure_decreases_at_full_fault(self):
        result = self._call(1.0)
        self.assertLess(result["oil_pressure_bar"], BASELINE["oil_pressure_bar"])

    def test_oil_temp_increases_at_full_fault(self):
        result = self._call(1.0)
        self.assertGreater(result["oil_temp_c"], BASELINE["oil_temp_c"])

    def test_vibration_increases_at_full_fault(self):
        result = self._call(1.0)
        self.assertGreater(result["vibration_g"], BASELINE["vibration_g"])


class TestMisfireFault(_FaultTestMixin, unittest.TestCase):
    fault_fn = staticmethod(inject_misfire_fault)
    # inject_misfire_fault accepts positional `cylinder` after `progress`
    # but we call it via **kwargs which won't conflict with positional.
    fault_kwargs = {}

    def _call(self, progress):
        # misfire has cylinder as a positional default, just pass progress
        return self.fault_fn(BASELINE, progress)

    def test_rpm_drops_at_full_fault(self):
        result = self._call(1.0)
        self.assertLess(result["rpm"], BASELINE["rpm"])

    def test_egt_drops_at_full_fault(self):
        result = self._call(1.0)
        self.assertLess(result["egt_c"], BASELINE["egt_c"])

    def test_vibration_increases_at_full_fault(self):
        result = self._call(1.0)
        self.assertGreater(result["vibration_g"], BASELINE["vibration_g"])


class TestSensorDriftFault(_FaultTestMixin, unittest.TestCase):
    fault_fn = staticmethod(inject_sensor_drift_fault)

    def _call(self, progress):
        return self.fault_fn(BASELINE, progress, channel="oil_pressure_bar")

    def test_drifted_channel_increases_at_full_fault(self):
        """Default drift is multiplicative upward (factor 1.15)."""
        result = self._call(1.0)
        self.assertGreater(result["oil_pressure_bar"], BASELINE["oil_pressure_bar"])

    def test_non_target_channels_unchanged(self):
        result = self._call(1.0)
        for key in ("egt_c", "cht_c", "oil_temp_c", "vibration_g"):
            self.assertAlmostEqual(
                result[key], BASELINE[key], places=4,
                msg=f"{key} should not be affected by sensor drift on oil_pressure_bar",
            )


class TestCombustionInstabilityFault(_FaultTestMixin, unittest.TestCase):
    fault_fn = staticmethod(inject_combustion_instability_fault)

    def test_egt_drops_at_full_fault(self):
        result = self._call(1.0)
        self.assertLess(result["egt_c"], BASELINE["egt_c"])

    def test_fuel_flow_increases_at_full_fault(self):
        result = self._call(1.0)
        self.assertGreater(result["fuel_flow_lph"], BASELINE["fuel_flow_lph"])

    def test_progress_zero_near_baseline(self):
        """Override: RPM has stochastic noise even at progress=0, but the
        noise amplitude is 0 so it should still match exactly."""
        result = self._call(0.0)
        for key in REQUIRED_KEYS:
            if isinstance(BASELINE[key], (int, float)):
                self.assertAlmostEqual(
                    result[key], BASELINE[key], places=4,
                    msg=f"{key} diverged at progress=0",
                )


class TestOverheatingFault(_FaultTestMixin, unittest.TestCase):
    fault_fn = staticmethod(inject_overheating_fault)

    def test_cht_increases_at_full_fault(self):
        result = self._call(1.0)
        self.assertGreater(result["cht_c"], BASELINE["cht_c"])

    def test_oil_temp_increases_at_full_fault(self):
        result = self._call(1.0)
        self.assertGreater(result["oil_temp_c"], BASELINE["oil_temp_c"])


class TestAlternatorFault(_FaultTestMixin, unittest.TestCase):
    fault_fn = staticmethod(inject_alternator_fault)

    def test_voltage_drops_at_full_fault(self):
        result = self._call(1.0)
        self.assertLess(result["alternator_v"], BASELINE["alternator_v"])

    def test_voltage_does_not_go_below_floor(self):
        """Even at full fault the voltage should not drop below the 10 V floor."""
        result = self._call(1.0)
        self.assertGreaterEqual(result["alternator_v"], 10.0)


if __name__ == "__main__":
    unittest.main()
