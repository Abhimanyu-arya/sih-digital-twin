"""
live_server.py

FastAPI WebSocket server for real-time streaming inference.
Each WebSocket connection gets its own LivePredictor instance (isolated
sliding-window state) so concurrent demos don't leak state.

Usage:
    python ai_layer/live_server.py          # starts on :8000
    python ai_layer/live_server.py --port 9000

WebSocket protocol:
    Client -> Server (JSON):
        {"action": "start", "mission_id": "mission_007", "speed": 10}
        {"action": "set_speed", "speed": 50}
        {"action": "reset"}
        {"action": "stop"}

    Server -> Client (JSON):
        {"type": "telemetry_frame", ...}      (same shape as demo_missions.json frames)
        {"type": "stream_started", ...}
        {"type": "stream_ended", ...}
        {"type": "error", "message": "..."}
"""

import os
import sys
import json
import math
import asyncio
import argparse
import numpy as np
import pandas as pd
import torch

# Ensure project root is on path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ai_layer.predict_pipeline import LivePredictor, DATASET_DIR, MODEL_PATH
from ai_layer.dashboard_export import (
    get_sensor_status_and_pct,
    translate_feature_to_shap_factor,
    ModelWrapper,
)
from ai_layer.rul_estimation.train_rul_model import RULConvNet, WINDOW_SIZE

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Digital Twin Live Inference Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared read-only resources (loaded once at startup)
# ---------------------------------------------------------------------------
SUMMARY_CSV = os.path.join(DATASET_DIR, "rul_summary.csv")
_summary_df = None
_shap_explainer = None
_shap_features = None
_device = None


def _get_summary_df():
    global _summary_df
    if _summary_df is None:
        _summary_df = pd.read_csv(SUMMARY_CSV)
    return _summary_df


def _get_shap_explainer():
    """Build the SHAP GradientExplainer once (read-only, thread-safe for inference)."""
    global _shap_explainer, _shap_features, _device
    if _shap_explainer is not None:
        return _shap_explainer, _shap_features

    import shap

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(MODEL_PATH, map_location=_device, weights_only=False)
    features = checkpoint["features"]
    raw_model = RULConvNet(in_channels=len(features)).to(_device)
    raw_model.load_state_dict(checkpoint["model_state_dict"])
    raw_model.eval()
    model = ModelWrapper(raw_model).to(_device)

    bg_samples = np.zeros((20, WINDOW_SIZE, len(features)), dtype=np.float32)
    bg_tensor = torch.tensor(bg_samples, dtype=torch.float32).transpose(1, 2).to(_device)
    _shap_explainer = shap.GradientExplainer(model, bg_tensor)
    _shap_features = features
    return _shap_explainer, features


# ---------------------------------------------------------------------------
# Demo mission specs (same as dashboard_export.py)
# ---------------------------------------------------------------------------
DEMO_SPECS = {
    "mission_007": {"label": "Oil Pressure System Degradation", "callsign": "FALCON-04 (MALE-UAV)"},
    "mission_033": {"label": "Ignition Circuit Misfire", "callsign": "REAPER-07 (MALE-UAV)"},
    "mission_012": {"label": "Coolant Loop Overheating", "callsign": "HERON-02 (TACTICAL-UAV)"},
    "mission_006": {"label": "Alternator Bus Voltage Collapse", "callsign": "SHADOW-09 (RECON-UAV)"},
    "mission_020": {"label": "Combustion Instability & Knock", "callsign": "EAGLE-01 (MALE-UAV)"},
    "mission_001": {"label": "Nominal Baseline Flight", "callsign": "PATROL-05 (ROTAX-912)"},
}


# ---------------------------------------------------------------------------
# LiveSession — one per WebSocket connection
# ---------------------------------------------------------------------------
class LiveSession:
    """Encapsulates all mutable state for a single streaming session."""

    def __init__(self, mission_id: str):
        csv_path = os.path.join(DATASET_DIR, f"{mission_id}.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Mission CSV not found: {csv_path}")

        self.mission_id = mission_id
        self.df = pd.read_csv(csv_path)
        self.total_rows = len(self.df)
        self.row_index = 0
        self.speed = 1
        self.running = False

        # Fresh predictor — clean history, window, anomaly state
        self.predictor = LivePredictor(model_path=MODEL_PATH)

        # Fault metadata
        summary = _get_summary_df()
        m_row = summary[summary["mission_id"] == mission_id]
        self.fault_type = m_row["fault_type"].values[0] if not m_row.empty else "none"

        spec = DEMO_SPECS.get(mission_id, {"label": mission_id, "callsign": "UNKNOWN"})
        self.fault_label = spec["label"]
        self.callsign = spec["callsign"]

        # Track first detection and cached SHAP
        self.t_first_detected = None
        self.cached_shap_factors = None

    def reset(self):
        """Reset to t=0 with fresh predictor state."""
        self.row_index = 0
        self.predictor = LivePredictor(model_path=MODEL_PATH)
        self.t_first_detected = None
        self.cached_shap_factors = None

    def build_frame(self, row_dict, compute_shap: bool = False):
        """Run inference on one row and return a dashboard-shaped frame dict."""
        ts = int(row_dict["timestamp"])

        # 1. Run predict pipeline
        res = self.predictor.process_telemetry(row_dict)
        status_str = res["status"]
        rul_sec = res["rul_seconds"]

        if self.predictor.anomaly_detected and self.t_first_detected is None:
            self.t_first_detected = self.predictor.t_detected

        # 2. MET clock
        hrs, mins, secs = ts // 3600, (ts % 3600) // 60, ts % 60
        met_formatted = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        # 3. Sensor readouts
        sensors_dict = {}
        for ch in ["rpm", "cht_c", "egt_c", "oil_pressure_bar", "oil_temp_c", "vibration_g", "alternator_v"]:
            val = row_dict.get(ch, 0.0)
            st, pct, display_val, limit_lbl = get_sensor_status_and_pct(ch, val)
            sensors_dict[ch] = {
                "value": round(float(val), 2),
                "display_value": display_val,
                "unit_label": limit_lbl,
                "status": st,
                "pct": pct,
            }

        # 4. System status logic (mirrors dashboard_export.py)
        persistence = (ts - self.t_first_detected) if self.t_first_detected and ts >= self.t_first_detected else 0
        is_healthy = self.fault_type in ("none", "healthy")
        caution_sensors = [ch for ch, s in sensors_dict.items() if s["status"] == "CAUTION"]
        critical_sensors = [ch for ch, s in sensors_dict.items() if s["status"] == "CRITICAL"]

        if len(critical_sensors) > 0 or (rul_sec is not None and rul_sec < 60):
            sys_state, sys_level = "CRITICAL", "LVL 3 EMERGENCY"
            sys_msg = f"CRITICAL - Failure Imminent ({self.fault_label})"
        elif self.predictor.anomaly_detected and not is_healthy:
            sys_state, sys_level = "DEGRADED", "LVL 2 CAUTION"
            sys_msg = f"DEGRADED - Anomaly Detected ({self.fault_label})"
        else:
            sys_state, sys_level = "NOMINAL", "LVL 1 NOMINAL"
            if caution_sensors:
                c_names = ", ".join([c.upper().replace("_C", "").replace("_BAR", "") for c in caution_sensors])
                sys_msg = f"NOMINAL ({len(caution_sensors)} Sensor Near Limit: {c_names})"
            else:
                sys_msg = "NOMINAL - Subsystem Operating Within Safe Calibration Limits"

        # 5. RUL payload
        if is_healthy or rul_sec is None:
            rul_data = {
                "seconds": None,
                "formatted": "N/A",
                "diff_vs_plan": "NOMINAL FLIGHT PLAN",
                "ci_lower_h": None,
                "ci_upper_h": None,
                "advisory": "ALL SYSTEMS NOMINAL. CONTINUATION ON ASSIGNED FLIGHT PATH PERMITTED.",
            }
        else:
            r_hrs = int(rul_sec // 3600)
            r_mins = int((rul_sec % 3600) // 60)
            rul_formatted = f"{r_hrs:02d}h {r_mins:02d}m" if r_hrs > 0 else f"{r_mins:02d}m {int(rul_sec % 60):02d}s"
            ci_lower = max(0.0, round((rul_sec * 0.9) / 3600.0, 1))
            ci_upper = round((rul_sec * 1.1) / 3600.0, 1)

            advisory_map = {
                "oil_pressure": "RECOMMENDATION: REDUCE RPM TO 4,800 (CRUISE) & INITIATE DESCENT / DIVERT.",
                "misfire": "RECOMMENDATION: SWITCH IGNITION CIRCUIT B & MAINTAIN MINIMUM STABLE RPM.",
                "overheating": "RECOMMENDATION: OPEN COOLANT LOUVERS & ENRICH MIXTURE; REDUCE POWER.",
                "alternator": "RECOMMENDATION: SHED NON-ESSENTIAL AVIONICS LOADS & LAND ON BATTERY RESERVE.",
            }
            advisory = "RECOMMENDATION: MONITOR TELEMETRY TRENDS & PREPARE FOR CONTINGENCY LANDING."
            for key, adv in advisory_map.items():
                if key in self.fault_type:
                    advisory = adv
                    break

            rul_data = {
                "seconds": round(rul_sec, 1),
                "formatted": rul_formatted,
                "diff_vs_plan": "-42m vs flight plan",
                "ci_lower_h": ci_lower,
                "ci_upper_h": ci_upper,
                "advisory": advisory,
            }

        # 6. SHAP factors
        shap_factors = self.cached_shap_factors
        if compute_shap and len(self.predictor.raw_window) == WINDOW_SIZE:
            try:
                explainer, features = _get_shap_explainer()
                device = _device
                w_arr = np.array(self.predictor.raw_window)
                w_tensor = torch.tensor(w_arr, dtype=torch.float32).unsqueeze(0).transpose(1, 2).to(device)
                s_vals = explainer.shap_values(w_tensor)
                s_arr = np.squeeze(s_vals, axis=-1)
                mean_imp = np.mean(np.abs(s_arr), axis=(0, 2))
                top_indices = np.argsort(mean_imp)[::-1][:3]
                top_scores = mean_imp[top_indices]
                tot_score = sum(top_scores) + 1e-6
                pcts = [int(round((sc / tot_score) * 100)) for sc in top_scores]
                if sum(pcts) != 100 and len(pcts) == 3:
                    pcts[0] += 100 - sum(pcts)

                shap_factors = []
                for rank_i, (idx_feat, w_pct) in enumerate(zip(top_indices, pcts), 1):
                    f_name = features[idx_feat]
                    s_factor = translate_feature_to_shap_factor(f_name, mean_imp[idx_feat], w_pct, rank_i, row_dict)
                    shap_factors.append(s_factor)
                self.cached_shap_factors = shap_factors
            except Exception:
                pass

        if shap_factors is None:
            shap_factors = [
                {
                    "rank": 1, "weight_pct": 70, "severity": "NOMINAL BASELINE",
                    "feature_raw": "oil_pressure_bar",
                    "title": "Main Gallery Lubrication Stability",
                    "description": "Main gallery oil pressure operating within nominal band.",
                    "value_str": f"{row_dict.get('oil_pressure_bar', 3.5):.2f} bar (NOMINAL)",
                    "correlation": 0.98,
                },
                {
                    "rank": 2, "weight_pct": 20, "severity": "NOMINAL BASELINE",
                    "feature_raw": "cht_c",
                    "title": "Cylinder Head Thermal Equilibrium",
                    "description": "Engine coolant and CHT operating within normal range.",
                    "value_str": f"{row_dict.get('cht_c', 105):.1f} C (NOMINAL)",
                    "correlation": 0.92,
                },
                {
                    "rank": 3, "weight_pct": 10, "severity": "NOMINAL BASELINE",
                    "feature_raw": "rpm",
                    "title": "Crankshaft Steady State Speed",
                    "description": "Engine RPM locked to commanded throttle curve.",
                    "value_str": f"{row_dict.get('rpm', 5000):.0f} RPM (NOMINAL)",
                    "correlation": 0.88,
                },
            ]

        return {
            "type": "telemetry_frame",
            "timestamp": ts,
            "met_formatted": met_formatted,
            "sensors": sensors_dict,
            "system_status": {
                "state": sys_state,
                "level": sys_level,
                "message": sys_msg,
                "anomaly_inception_s": self.t_first_detected if self.t_first_detected else 0,
                "persistence_s": persistence,
            },
            "rul": rul_data,
            "shap_factors": shap_factors,
            "progress_pct": round((self.row_index / max(1, self.total_rows)) * 100, 1),
            "total_rows": self.total_rows,
        }


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/api/missions")
def list_missions():
    """List available demo missions."""
    summary = _get_summary_df()
    missions = []
    for mid, spec in DEMO_SPECS.items():
        csv_path = os.path.join(DATASET_DIR, f"{mid}.csv")
        if not os.path.exists(csv_path):
            continue
        row = summary[summary["mission_id"] == mid]
        fault_type = row["fault_type"].values[0] if not row.empty else "none"
        df = pd.read_csv(csv_path)
        missions.append({
            "mission_id": mid,
            "fault_type": fault_type,
            "fault_label": spec["label"],
            "callsign": spec["callsign"],
            "total_rows": len(df),
            "duration_s": len(df),
        })
    return {"missions": missions}


# ---------------------------------------------------------------------------
# WebSocket streaming
# ---------------------------------------------------------------------------
@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    session: LiveSession | None = None
    stream_task: asyncio.Task | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            action = msg.get("action", "")

            if action == "start":
                mission_id = msg.get("mission_id", "mission_007")
                speed = max(1, min(100, int(msg.get("speed", 10))))

                # Cleanly tear down any existing stream and task first
                if session:
                    session.running = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                    try:
                        await stream_task
                    except (asyncio.CancelledError, Exception):
                        pass

                try:
                    session = LiveSession(mission_id)
                    session.speed = speed
                except FileNotFoundError as e:
                    await ws.send_json({"type": "error", "message": str(e)})
                    continue

                await ws.send_json({
                    "type": "stream_started",
                    "mission_id": mission_id,
                    "total_rows": session.total_rows,
                    "fault_label": session.fault_label,
                    "callsign": session.callsign,
                })

                # Start streaming in background task
                session.running = True
                stream_task = asyncio.create_task(_stream_loop(ws, session))

            elif action == "set_speed":
                if session:
                    session.speed = max(1, min(100, int(msg.get("speed", 10))))

            elif action == "reset":
                if session:
                    session.running = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                    try:
                        await stream_task
                    except (asyncio.CancelledError, Exception):
                        pass

                if session:
                    session.reset()
                    await ws.send_json({
                        "type": "stream_started",
                        "mission_id": session.mission_id,
                        "total_rows": session.total_rows,
                        "fault_label": session.fault_label,
                        "callsign": session.callsign,
                    })
                    session.running = True
                    stream_task = asyncio.create_task(_stream_loop(ws, session))

            elif action == "stop":
                if session:
                    session.running = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()

    except WebSocketDisconnect:
        if session:
            session.running = False
        if stream_task and not stream_task.done():
            stream_task.cancel()
    except Exception:
        if session:
            session.running = False
        if stream_task and not stream_task.done():
            stream_task.cancel()


async def _stream_loop(ws: WebSocket, session: LiveSession):
    """Push telemetry frames at the configured speed."""
    try:
        while session.running and session.row_index < session.total_rows:
            row = session.df.iloc[session.row_index]
            row_dict = row.to_dict()

            # Compute SHAP every 5th row (matches dashboard_export.py)
            compute_shap = (session.row_index % 5 == 0)
            frame = session.build_frame(row_dict, compute_shap=compute_shap)

            await ws.send_json(frame)
            session.row_index += 1

            # Sleep based on speed multiplier
            await asyncio.sleep(1.0 / session.speed)

        if session.running:
            await ws.send_json({
                "type": "stream_ended",
                "mission_id": session.mission_id,
            })
            session.running = False
    except (WebSocketDisconnect, asyncio.CancelledError):
        session.running = False
    except Exception:
        session.running = False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Digital Twin Live Inference Server")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    print(f"Starting live inference server on {args.host}:{args.port}")
    print(f"Dataset directory: {DATASET_DIR}")
    print(f"Model path: {MODEL_PATH}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
