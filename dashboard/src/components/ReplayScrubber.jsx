import React from 'react';

export default function ReplayScrubber({
  currentIndex,
  totalFrames,
  currentFrame,
  isPlaying,
  playbackSpeed,
  tFirstDetected,
  onSeek,
  onTogglePlay,
  onSetSpeed,
  onJumpToAnomaly
}) {
  const metStr = currentFrame?.met_formatted || "00:00:00";
  const pct = totalFrames > 1 ? (currentIndex / (totalFrames - 1)) * 100 : 0;

  return (
    <section className="bg-surface-container-low border border-outline-variant/40 rounded p-unit-sm flex flex-col gap-unit-xs">
      {/* Top telemetry status line */}
      <div className="flex items-center justify-between font-label-micro text-label-micro">
        <div className="flex items-center gap-unit-md">
          <span className="text-primary font-bold uppercase flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">timeline</span>
            MISSION REPLAY SCRUBBER
          </span>
          <span className="text-on-surface-variant">TIMELINE RANGE: T+00:00:00 -&gt; T+{(totalFrames - 1)}s</span>
        </div>
        <div className="flex items-center gap-unit-sm">
          <span className="text-outline">CURSOR MET:</span>
          <span className="font-telemetry-data text-telemetry-data text-primary font-bold">{metStr}</span>
          <span className="text-outline">FRAME:</span>
          <span className="font-telemetry-data text-telemetry-data text-on-surface">#{currentIndex} / {totalFrames}</span>
        </div>
      </div>

      {/* Telemetry Density Heat-Strip Track */}
      <div className="relative w-full h-3 bg-surface-container-lowest rounded overflow-hidden flex">
        {/* Nominal portion */}
        <div 
          className="h-full bg-secondary/70"
          style={{ width: `${tFirstDetected ? (tFirstDetected / totalFrames) * 100 : 100}%` }}
          title="Nominal Telemetry Region"
        />
        {/* Degraded portion */}
        {tFirstDetected && (
          <div 
            className="h-full bg-tertiary"
            style={{ width: `${((totalFrames - tFirstDetected) / totalFrames) * 100}%` }}
            title="Degraded Telemetry Region"
          />
        )}
        {/* Needle */}
        <div 
          className="absolute top-0 bottom-0 w-1 bg-primary shadow-[0_0_8px_#4cd7f6] transition-all duration-75"
          style={{ left: `${pct}%` }}
        />
      </div>

      {/* Milestone Interactive Slider Track */}
      <div className="relative w-full py-1">
        <input 
          type="range"
          min={0}
          max={totalFrames - 1}
          value={currentIndex}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="w-full accent-primary bg-surface-container-high h-1.5 rounded cursor-ew-resize appearance-none"
        />
        <div className="flex justify-between items-center font-label-micro text-label-micro text-outline mt-1 px-1">
          <span className="hover:text-on-surface cursor-pointer" onClick={() => onSeek(0)}>[TAKEOFF T+00]</span>
          {tFirstDetected && (
            <span 
              className="text-tertiary font-bold hover:underline cursor-pointer flex items-center gap-0.5"
              onClick={onJumpToAnomaly}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
              [ANOMALY T+{tFirstDetected}s]
            </span>
          )}
          <span className="hover:text-on-surface cursor-pointer" onClick={() => onSeek(totalFrames - 1)}>[END T+{totalFrames - 1}s]</span>
        </div>
      </div>

      {/* Scrubber Controls */}
      <div className="flex flex-wrap items-center justify-between gap-unit-sm pt-unit-2xs border-t border-outline-variant/30">
        <div className="flex items-center gap-unit-xs">
          <button 
            type="button"
            onClick={onTogglePlay}
            className="w-7 h-7 bg-surface-container-high border border-outline-variant text-on-surface rounded flex items-center justify-center hover:border-primary hover:text-primary transition-colors"
            title="Play / Pause Telemetry Stream"
          >
            <span className="material-symbols-outlined text-[16px]">
              {isPlaying ? "pause" : "play_arrow"}
            </span>
          </button>

          <div className="flex items-center bg-surface-container-high border border-outline-variant rounded font-label-code text-label-code p-0.5">
            {[1, 5, 10].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSetSpeed(s)}
                className={`px-1.5 py-0.5 rounded ${playbackSpeed === s ? 'text-primary font-bold bg-surface-container-highest' : 'text-outline hover:text-on-surface'}`}
              >
                {s}x
              </button>
            ))}
          </div>

          {tFirstDetected && (
            <button 
              type="button"
              onClick={onJumpToAnomaly}
              className="px-unit-xs py-1 bg-tertiary-container/30 border border-tertiary/50 text-tertiary rounded font-label-code text-label-code hover:bg-tertiary-container/50 transition-colors flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[13px]">crisis_alert</span>
              JUMP TO ANOMALY (T+{tFirstDetected}s)
            </button>
          )}
        </div>

        <div className="flex items-center gap-unit-md font-label-micro text-label-micro text-outline">
          <span>BLACKBOX DATA: DUAL SSD WRITE-THROUGH</span>
          <span className="text-secondary flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span> 0 PACKETS DROPPED
          </span>
        </div>
      </div>
    </section>
  );
}
