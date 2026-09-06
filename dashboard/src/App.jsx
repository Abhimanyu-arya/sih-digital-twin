import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import HealthStatusMonitor from './components/HealthStatusMonitor';
import RulProjectionCard from './components/RulProjectionCard';
import SensorMatrix from './components/SensorMatrix';
import DiagnosticInferenceEngine from './components/DiagnosticInferenceEngine';
import RulChart from './components/RulChart';
import DebugJsonInspector from './components/DebugJsonInspector';

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedMissionId, setSelectedMissionId] = useState("mission_007");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [zuluClock, setZuluClock] = useState("");
  const [isDebugOpen, setIsDebugOpen] = useState(false);

  const playTimerRef = useRef(null);

  // Fetch JSON export
  useEffect(() => {
    fetch('/demo_missions.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then((json) => {
        setData(json);
        if (json.missions && json.missions.length > 0) {
          setSelectedMissionId(json.missions[0].mission_id);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load demo_missions.json:", err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Reset index and playback whenever selected mission changes
  useEffect(() => {
    setCurrentIndex(0);
    setIsPlaying(false);
  }, [selectedMissionId]);

  // Update Zulu clock
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setZuluClock(now.toISOString().substring(11, 22) + " Z");
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // Playback timer
  useEffect(() => {
    if (isPlaying) {
      const intervalMs = Math.max(50, 1000 / playbackSpeed);
      playTimerRef.current = setInterval(() => {
        setCurrentIndex((prev) => {
          const currentMission = data?.missions?.find(m => m.mission_id === selectedMissionId);
          const maxFrames = currentMission?.telemetry?.length || 1;
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
  }, [isPlaying, playbackSpeed, selectedMissionId, data]);

  const handleSelectMission = (mid) => {
    setSelectedMissionId(mid);
    setCurrentIndex(0);
    setIsPlaying(false);
  };

  const handleJumpToAnomaly = () => {
    const currentMission = data?.missions?.find(m => m.mission_id === selectedMissionId);
    if (currentMission && currentMission.t_first_detected) {
      const idx = currentMission.telemetry.findIndex(f => f.timestamp >= currentMission.t_first_detected);
      if (idx !== -1) {
        setCurrentIndex(idx);
      }
    }
  };

  if (loading) {
    return (
      <div className="h-screen bg-background text-on-surface flex items-center justify-center flex-col gap-4 font-telemetry-data">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span className="text-primary tracking-widest uppercase">INITIALIZING TRIPLE T AVIONICS TELEMETRY ENGINE...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-background text-error flex items-center justify-center flex-col gap-4 font-telemetry-data">
        <span className="text-xl font-bold">ERROR LOADING TELEMETRY DATA</span>
        <span className="text-sm text-on-surface-variant">{error}</span>
      </div>
    );
  }

  const missions = data?.missions || [];
  const currentMission = missions.find(m => m.mission_id === selectedMissionId) || missions[0];
  const telemetry = currentMission?.telemetry || [];
  const totalFrames = telemetry.length;
  
  // Safe indexing bounds clamp
  const validIndex = Math.min(currentIndex, Math.max(0, totalFrames - 1));
  const currentFrame = telemetry[validIndex] || telemetry[0] || {};
  const currentSystemState = currentFrame.system_status?.state || "NOMINAL";

  return (
    <div className="h-screen flex flex-col bg-surface text-on-surface overflow-hidden">
      {/* Top Header Bar */}
      <Header 
        currentMission={currentMission}
        missions={missions}
        onSelectMission={handleSelectMission}
        metFormatted={currentFrame.met_formatted}
        zuluClock={zuluClock}
        systemState={currentSystemState}
        isDebugOpen={isDebugOpen}
        onToggleDebug={() => setIsDebugOpen(!isDebugOpen)}
      />

      {/* Main Workspace Canvas (Full Width, Sidebar Removed) */}
      <div className="flex flex-1 overflow-hidden">
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
                systemStatus={currentFrame.system_status}
                sensors={currentFrame.sensors}
              />
            </div>
            <div className="lg:col-span-6">
              <RulProjectionCard 
                rulPayload={currentFrame.rul}
              />
            </div>
          </section>

          {/* 2. Sensor Telemetry Matrix */}
          <SensorMatrix 
            sensors={currentFrame.sensors}
          />

          {/* 3. Diagnostic Inference Engine (SHAP) */}
          <DiagnosticInferenceEngine 
            shapFactors={currentFrame.shap_factors}
            faultLabel={currentMission.fault_label}
          />

          {/* 4. Combined RUL Vector Line Chart & Mission Replay Scrubber */}
          <RulChart 
            telemetry={telemetry}
            currentIndex={validIndex}
            faultStartS={currentMission.fault_start_s}
            tFirstDetected={currentMission.t_first_detected}
            totalFrames={totalFrames}
            currentFrame={currentFrame}
            isPlaying={isPlaying}
            playbackSpeed={playbackSpeed}
            onSeek={(idx) => setCurrentIndex(idx)}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
            onSetSpeed={(speed) => setPlaybackSpeed(speed)}
            onJumpToAnomaly={handleJumpToAnomaly}
          />

        </main>
      </div>
    </div>
  );
}


