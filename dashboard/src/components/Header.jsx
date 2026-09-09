import React, { useState, useRef, useEffect } from 'react';
import LiveIndicator from './LiveIndicator';

export default function Header({ 
  currentMission, 
  missions, 
  onSelectMission, 
  metFormatted, 
  zuluClock,
  systemState,
  isDebugOpen,
  onToggleDebug,
  mode,
  onSetMode,
  isLiveConnected,
  isLiveStreaming,
  liveSpeed = 10,
  onLiveSpeedChange,
  onLiveReset,
}) {
  const [audioMuted, setAudioMuted] = useState(false);
  const [isOverflowOpen, setIsOverflowOpen] = useState(false);
  const overflowRef = useRef(null);

  const isCritical = systemState === "CRITICAL";
  const isDegraded = systemState === "DEGRADED";

  let statusBadgeStyle = "bg-secondary/20 text-secondary border-secondary/40";
  if (isCritical) {
    statusBadgeStyle = "bg-error/20 text-error border-error animate-pulse font-bold";
  } else if (isDegraded) {
    statusBadgeStyle = "bg-tertiary/20 text-tertiary border-tertiary/40 font-bold";
  }

  // Close overflow menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (overflowRef.current && !overflowRef.current.contains(event.target)) {
        setIsOverflowOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="h-14 bg-surface-container-lowest border-b border-outline-variant/30 px-4 flex items-center justify-between flex-none z-50 overflow-visible relative">
      {/* Left Branding, Mission Dropdown & Status Badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-primary/20 border border-primary flex items-center justify-center text-primary font-bold font-label-code text-xs">
            TT
          </div>
          <div className="flex flex-col justify-center">
            <span className="font-headline-sm text-xs text-on-surface tracking-wider uppercase font-bold">TRIPLE T</span>
            <span className="font-label-micro text-[10px] text-secondary font-semibold">
              {currentMission?.callsign || "FALCON-04 (MALE UAV)"}
            </span>
          </div>
        </div>

        <div className="h-6 w-[1px] bg-outline-variant/40 hidden sm:block"></div>

        {/* Mission Selector Dropdown */}
        <div className="flex items-center gap-1.5 bg-surface-container-low px-2.5 py-1 border border-outline-variant/40 rounded">
          <span className="font-label-micro text-[10px] text-outline uppercase hidden md:inline">MISSION:</span>
          <select 
            value={currentMission?.mission_id || ""}
            onChange={(e) => onSelectMission(e.target.value)}
            className="bg-transparent font-telemetry-data text-primary font-semibold border-none focus:outline-none focus:ring-0 cursor-pointer text-xs"
          >
            {missions.map((m) => (
              <option key={m.mission_id} value={m.mission_id} className="bg-surface-container-low text-on-surface">
                #{m.mission_id.toUpperCase()} — {m.fault_label}
              </option>
            ))}
          </select>
        </div>

        {/* Essential Overall Status Badge */}
        <span className={`px-2 py-0.5 rounded border font-label-code text-xs flex items-center gap-1.5 ${statusBadgeStyle}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isCritical ? 'bg-error' : isDegraded ? 'bg-tertiary' : 'bg-secondary'}`}></span>
          <span>{systemState || 'NOMINAL'}</span>
        </span>
      </div>

      {/* Middle Mode Selector & Live Controls */}
      <div className="flex items-center gap-2">
        {/* Mode Switcher: REPLAY vs LIVE */}
        <div className="flex items-center bg-surface-container-low p-0.5 border border-outline-variant/40 rounded font-label-code text-xs">
          <button
            type="button"
            onClick={() => onSetMode("replay")}
            className={`px-2.5 py-1 rounded transition-colors ${
              mode === "replay" 
                ? "bg-surface-container-high text-primary font-bold shadow-sm" 
                : "text-outline hover:text-on-surface"
            }`}
          >
            REPLAY
          </button>
          <button
            type="button"
            onClick={() => onSetMode("live")}
            className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 ${
              mode === "live" 
                ? "bg-primary/20 text-primary font-bold border border-primary/40 shadow-sm" 
                : "text-outline hover:text-on-surface"
            }`}
          >
            <span>LIVE</span>
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
          </button>
        </div>

        {/* Live Controls (when mode === "live") */}
        {mode === "live" && (
          <div className="flex items-center gap-2">
            <LiveIndicator isStreaming={isLiveStreaming} isConnected={isLiveConnected} />
            
            {/* Speed selector (defaulting to 10x) */}
            <div className="flex items-center gap-1 bg-surface-container-low px-2 py-1 border border-outline-variant/40 rounded text-xs font-label-code">
              <span className="text-outline text-[10px]">SPEED:</span>
              <select
                value={liveSpeed}
                onChange={(e) => onLiveSpeedChange && onLiveSpeedChange(Number(e.target.value))}
                className="bg-transparent text-primary font-bold focus:outline-none cursor-pointer"
              >
                <option value={1} className="bg-surface-container text-on-surface">1x (Real-time)</option>
                <option value={5} className="bg-surface-container text-on-surface">5x</option>
                <option value={10} className="bg-surface-container text-on-surface">10x (Demo Default)</option>
                <option value={50} className="bg-surface-container text-on-surface">50x (Fast)</option>
              </select>
            </div>

            {/* Reset Live Session Button */}
            <button
              type="button"
              onClick={onLiveReset}
              className="px-2 py-1 bg-surface-container-low hover:bg-surface-container-high border border-outline-variant/40 text-outline hover:text-on-surface rounded font-label-code text-xs flex items-center gap-1"
              title="Reset Live Stream to T=0"
            >
              <span className="material-symbols-outlined text-[14px]">restart_alt</span>
              <span className="hidden md:inline">RESET</span>
            </button>
          </div>
        )}
      </div>

      {/* Right Controls: Single Compact Readout + Overflow Menu */}
      <div className="flex items-center gap-3">
        {/* Single Compact Clock Readout */}
        <div className="hidden sm:flex items-center gap-2 bg-surface-container-low px-2.5 py-1 border border-outline-variant/30 rounded font-telemetry-data text-[11px] text-on-surface-variant">
          <span className="text-outline">UTC:</span>
          <span className="text-on-surface font-semibold">{zuluClock || "--:--:-- Z"}</span>
          <span className="text-outline-variant">|</span>
          <span className="text-outline">MET:</span>
          <span className="text-primary font-bold">{metFormatted || "00:00:00"}</span>
        </div>

        {/* Overflow Menu ("..." Icon) */}
        <div className="relative" ref={overflowRef}>
          <button 
            type="button"
            onClick={() => setIsOverflowOpen(!isOverflowOpen)}
            className={`w-8 h-8 rounded border transition-colors flex items-center justify-center ${isOverflowOpen ? 'bg-primary text-on-primary border-primary' : 'bg-surface-container-high border-outline-variant text-on-surface hover:border-primary'}`}
            title="Dashboard Settings & Overflow Controls"
          >
            <span className="material-symbols-outlined text-[18px]">more_vert</span>
          </button>

          {/* Dropdown Menu Popup */}
          {isOverflowOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-surface-container-high border border-outline-variant rounded-md shadow-xl py-2 z-50 flex flex-col gap-1">
              <div className="px-3 py-1 text-[10px] font-label-micro text-outline uppercase border-b border-outline-variant/30 mb-1">
                OVERFLOW & DEBUG CONTROLS
              </div>

              {/* Debug Toggle */}
              <button
                type="button"
                onClick={() => { onToggleDebug(); setIsOverflowOpen(false); }}
                className="w-full px-3 py-1.5 text-left text-xs font-label-code text-on-surface hover:bg-surface-container-highest flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-primary">code</span>
                  <span>DEBUG RAW JSON</span>
                </span>
                <span className="text-[10px] text-outline">{isDebugOpen ? "ON" : "OFF"}</span>
              </button>

              {/* Audio Toggle */}
              <button
                type="button"
                onClick={() => setAudioMuted(!audioMuted)}
                className="w-full px-3 py-1.5 text-left text-xs font-label-code text-on-surface hover:bg-surface-container-highest flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-secondary">
                    {audioMuted ? "volume_off" : "volume_up"}
                  </span>
                  <span>AUDIO ALARM</span>
                </span>
                <span className="text-[10px] text-outline">{audioMuted ? "MUTED" : "ACTIVE"}</span>
              </button>

              {/* Master Warn */}
              <button
                type="button"
                onClick={() => {
                  alert(`MASTER WARNING STATUS: ${systemState || 'NOMINAL'} (${currentMission?.fault_label})`);
                  setIsOverflowOpen(false);
                }}
                className="w-full px-3 py-1.5 text-left text-xs font-label-code hover:bg-surface-container-highest flex items-center justify-between text-tertiary"
              >
                <span className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-tertiary">warning</span>
                  <span>MASTER WARN</span>
                </span>
                <span className="text-[10px] font-bold">{systemState || 'NOMINAL'}</span>
              </button>
            </div>
          )}
        </div>

        {/* User Avatar */}
        <div className="w-7 h-7 rounded-full bg-primary/30 border border-primary/50 flex items-center justify-center flex-none">
          <span className="material-symbols-outlined text-primary text-[16px]">person</span>
        </div>
      </div>
    </header>
  );
}
