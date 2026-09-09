import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import HealthStatusMonitor from './components/HealthStatusMonitor';
import RulProjectionCard from './components/RulProjectionCard';
import SensorMatrix from './components/SensorMatrix';
import DiagnosticInferenceEngine from './components/DiagnosticInferenceEngine';
import RulChart from './components/RulChart';
import DebugJsonInspector from './components/DebugJsonInspector';
import useLiveStream from './hooks/useLiveStream';

export default function App() {
  // ── Shared state ──
  const [mode, setMode] = useState("replay"); // "replay" | "live"
  const [selectedMissionId, setSelectedMissionId] = useState("mission_007");
  const [zuluClock, setZuluClock] = useState("");
  const [isDebugOpen, setIsDebugOpen] = useState(false);

  // ── Replay mode state: manifest + per-mission cache ──
  const [manifest, setManifest] = useState(null);
  const [loadedMissions, setLoadedMissions] = useState({});
  const [loadingManifest, setLoadingManifest] = useState(true);
  const [loadingMission, setLoadingMission] = useState(false);
  const [error, setError] = useState(null);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const playTimerRef = useRef(null);

  // ── Live mode state (default 10x speed) ──
  const [liveSpeed, setLiveSpeed] = useState(10);
  const live = useLiveStream('/ws/stream');

  // ── Zulu clock ──
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setZuluClock(now.toISOString().substring(11, 22) + " Z");
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // ── 1. Fetch lightweight mission manifest ──
  useEffect(() => {
    fetch('/demo_missions.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then((json) => {
        setManifest(json);
        if (json.missions && json.missions.length > 0) {
          setSelectedMissionId(json.missions[0].mission_id);
        }
        setLoadingManifest(false);
      })
      .catch((err) => {
        console.error("Failed to load demo_missions.json manifest:", err);
        setError(err.message);
        setLoadingManifest(false);
      });
  }, []);

  // ── 2. On-demand fetch of selected per-mission JSON file ──
  useEffect(() => {
    if (!selectedMissionId || mode !== "replay") return;
    if (loadedMissions[selectedMissionId]) return; // already cached

    setLoadingMission(true);
    fetch(`/missions/${selectedMissionId}.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then((missionData) => {
        setLoadedMissions((prev) => ({ ...prev, [selectedMissionId]: missionData }));
        setLoadingMission(false);
      })
      .catch((err) => {
        console.error(`Failed to load /missions/${selectedMissionId}.json:`, err);
        setLoadingMission(false);
      });
  }, [selectedMissionId, mode, loadedMissions]);

  // ── Reset replay state when mission changes ──
  useEffect(() => {
    setCurrentIndex(0);
    setIsPlaying(false);
  }, [selectedMissionId]);

  // ── Replay playback timer ──
  useEffect(() => {
    if (mode !== "replay") return;
    if (isPlaying) {
      const activeMission = loadedMissions[selectedMissionId];
      const maxFrames = activeMission?.telemetry?.length || 1;
      const intervalMs = Math.max(50, 1000 / playbackSpeed);

      playTimerRef.current = setInterval(() => {
        setCurrentIndex((prev) => {
          if (prev >= maxFrames - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, playbackSpeed, selectedMissionId, loadedMissions, mode]);

  // ── Mode switching ──
  const handleSetMode = (newMode) => {
    if (newMode === mode) return;
    if (newMode === "live") {
      setIsPlaying(false);
      live.start(selectedMissionId, liveSpeed);
    } else {
      live.stop();
      live.disconnect();
      setCurrentIndex(0);
    }
    setMode(newMode);
  };

  const handleSelectMission = (mid) => {
    setSelectedMissionId(mid);
    setCurrentIndex(0);
    setIsPlaying(false);
    if (mode === "live") {
      live.start(mid, liveSpeed);
    }
  };

  const handleLiveSpeedChange = (speed) => {
    setLiveSpeed(speed);
    live.setSpeed(speed);
  };

  const handleLiveReset = () => {
    live.reset();
  };

  const handleJumpToAnomaly = () => {
    if (mode !== "replay") return;
    const activeMission = loadedMissions[selectedMissionId];
    if (activeMission && activeMission.t_first_detected) {
      const idx = activeMission.telemetry.findIndex(f => f.timestamp >= activeMission.t_first_detected);
      if (idx !== -1) {
        setCurrentIndex(idx);
      }
    }
  };

  // ── Loading manifest state ──
  if (loadingManifest) {
    return (
      <div className="h-screen bg-background text-on-surface flex items-center justify-center flex-col gap-4 font-telemetry-data">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span className="text-primary tracking-widest uppercase">INITIALIZING TRIPLE T AVIONICS TELEMETRY ENGINE...</span>
      </div>
    );
  }

  // ── Replay error state ──
  if (error && mode === "replay") {
    return (
      <div className="h-screen bg-background text-error flex items-center justify-center flex-col gap-4 font-telemetry-data">
        <span className="text-xl font-bold">ERROR LOADING TELEMETRY MANIFEST</span>
        <span className="text-sm text-on-surface-variant">{error}</span>
      </div>
    );
  }

  // ── Derive current frame & mission from either mode ──
  const manifestMissions = manifest?.missions || [];
  const manifestMeta = manifestMissions.find(m => m.mission_id === selectedMissionId) || manifestMissions[0];
  const activeLoadedMission = loadedMissions[selectedMissionId];

  let currentMission, currentFrame, telemetry, totalFrames;

  if (mode === "live" && live.currentFrame) {
    currentFrame = live.currentFrame;
    telemetry = live.history;
    totalFrames = live.streamMeta?.total_rows || live.history.length;
    currentMission = {
      mission_id: selectedMissionId,
      callsign: live.streamMeta?.callsign || manifestMeta?.callsign || "",
      fault_label: live.streamMeta?.fault_label || manifestMeta?.fault_label || "",
      fault_type: manifestMeta?.fault_type || "",
      fault_start_s: manifestMeta?.fault_start_s || 0,
      t_first_detected: currentFrame?.system_status?.anomaly_inception_s || 0,
      total_duration_s: totalFrames,
      telemetry: telemetry,
    };
  } else {
    currentMission = activeLoadedMission || manifestMeta;
    telemetry = activeLoadedMission?.telemetry || [];
    totalFrames = telemetry.length;
    const validIndex = Math.min(currentIndex, Math.max(0, totalFrames - 1));
    currentFrame = telemetry[validIndex] || telemetry[0] || {};
  }

  const currentSystemState = currentFrame?.system_status?.state || "NOMINAL";

  return (
    <div className="h-screen flex flex-col bg-surface text-on-surface overflow-hidden">
      {/* Top Header Bar */}
      <Header 
        currentMission={currentMission}
        missions={manifestMissions}
        onSelectMission={handleSelectMission}
        metFormatted={currentFrame?.met_formatted}
        zuluClock={zuluClock}
        systemState={currentSystemState}
        isDebugOpen={isDebugOpen}
        onToggleDebug={() => setIsDebugOpen(!isDebugOpen)}
        mode={mode}
        onSetMode={handleSetMode}
        isLiveConnected={live.isConnected}
        isLiveStreaming={live.isStreaming}
        liveSpeed={liveSpeed}
        onLiveSpeedChange={handleLiveSpeedChange}
        onLiveReset={handleLiveReset}
      />

      {/* Main Workspace Canvas */}
      <div className="flex flex-1 overflow-hidden flex-col">
        {/* Error banner for Live Server unreachable / connection lost */}
        {mode === "live" && (live.serverUnreachable || live.connectionLost) && (
          <div className="bg-error/15 border-b border-error/40 px-4 py-2.5 flex items-center justify-between font-label-code text-xs text-error">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">wifi_off</span>
              <span className="font-bold">
                {live.serverUnreachable 
                  ? "Live server not reachable — start ai_layer/live_server.py" 
                  : "Connection lost to live inference server"}
              </span>
            </div>
            <button
              type="button"
              onClick={() => live.reconnect()}
              className="px-3 py-1 bg-error text-on-error hover:bg-error/90 rounded font-bold transition-colors flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[14px]">refresh</span>
              <span>RECONNECT</span>
            </button>
          </div>
        )}

        {/* Loading spinner overlay when fetching per-mission JSON in replay mode */}
        {mode === "replay" && loadingMission && !activeLoadedMission && (
          <div className="bg-primary/10 border-b border-primary/30 px-4 py-2 flex items-center gap-2 font-label-code text-xs text-primary">
            <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
            <span>LOADING MISSION DATA ({selectedMissionId.toUpperCase()})...</span>
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 w-full">
          
          {/* Debug Raw JSON Inspector Overlay */}
          {isDebugOpen && (
            <DebugJsonInspector 
              currentFrame={currentFrame}
              currentMission={currentMission}
              onClose={() => setIsDebugOpen(false)}
            />
          )}

          {/* 1. Top Health Status & RUL Projection Row */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            <div className="lg:col-span-6">
              <HealthStatusMonitor 
                systemStatus={currentFrame?.system_status}
                sensors={currentFrame?.sensors}
              />
            </div>
            <div className="lg:col-span-6">
              <RulProjectionCard 
                rulPayload={currentFrame?.rul}
              />
            </div>
          </section>

          {/* 2. Sensor Telemetry Matrix */}
          <SensorMatrix 
            sensors={currentFrame?.sensors}
          />

          {/* 3. Diagnostic Inference Engine (SHAP) */}
          <DiagnosticInferenceEngine 
            shapFactors={currentFrame?.shap_factors}
            faultLabel={currentMission?.fault_label}
          />

          {/* 4. RUL Chart & Replay/Live Controls */}
          <RulChart 
            telemetry={telemetry}
            currentIndex={mode === "live" ? Math.max(0, telemetry.length - 1) : Math.min(currentIndex, Math.max(0, totalFrames - 1))}
            faultStartS={currentMission?.fault_start_s}
            tFirstDetected={currentMission?.t_first_detected}
            totalFrames={totalFrames}
            currentFrame={currentFrame}
            isPlaying={mode === "live" ? live.isStreaming : isPlaying}
            playbackSpeed={mode === "live" ? liveSpeed : playbackSpeed}
            onSeek={mode === "live" ? undefined : (idx) => setCurrentIndex(idx)}
            onTogglePlay={mode === "live" ? undefined : () => setIsPlaying(!isPlaying)}
            onSetSpeed={mode === "live" ? undefined : (speed) => setPlaybackSpeed(speed)}
            onJumpToAnomaly={mode === "live" ? undefined : handleJumpToAnomaly}
            isLiveMode={mode === "live"}
          />

        </main>
      </div>
    </div>
  );
}
