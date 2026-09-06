import React from 'react';

export default function RulChart({ 
  telemetry, 
  currentIndex, 
  faultStartS, 
  tFirstDetected,
  totalFrames,
  currentFrame,
  isPlaying,
  playbackSpeed,
  onSeek,
  onTogglePlay,
  onSetSpeed,
  onJumpToAnomaly
}) {
  if (!telemetry || telemetry.length === 0) return null;

  const frame = currentFrame || telemetry[currentIndex] || telemetry[0];
  const maxTime = telemetry[telemetry.length - 1].timestamp || 600;
  const currentTs = frame.timestamp;
  const metStr = frame?.met_formatted || "00:00:00";
  const numFrames = totalFrames || telemetry.length;

  // Map timestamp (0 -> maxTime) to X (40 -> 880)
  // Map RUL (0 -> 18000s [5h]) to Y (145 -> 15)
  const mapX = (t) => 40 + (t / maxTime) * (880 - 40);
  const mapY = (rSec) => {
    if (rSec === null || rSec === undefined) return 15;
    const maxRulSec = 18000.0;
    const norm = Math.min(1.0, Math.max(0.0, rSec / maxRulSec));
    return 145 - norm * (145 - 15);
  };

  // Build historical RUL path string
  const histPoints = telemetry.slice(0, currentIndex + 1).map((f) => {
    const x = mapX(f.timestamp);
    const y = mapY(f.rul.seconds);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const histPathD = histPoints.length > 0 ? `M${histPoints.join(' L')}` : "";

  // Projected trajectory path string
  const projPoints = telemetry.slice(currentIndex).map((f) => {
    const x = mapX(f.timestamp);
    const y = mapY(f.rul.seconds);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const projPathD = projPoints.length > 0 ? `M${projPoints.join(' L')}` : "";

  const cursorX = mapX(currentTs);
  const cursorY = mapY(frame.rul.seconds);
  const anomalyX = tFirstDetected ? mapX(tFirstDetected) : null;
  const pct = numFrames > 1 ? (currentIndex / (numFrames - 1)) * 100 : 0;

  return (
    <section className="bg-surface-container-low border border-outline-variant/40 rounded p-3 flex flex-col gap-2">
      {/* Top Header & Telemetry Controls Line */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[18px]">show_chart</span>
          <h3 className="font-headline-sm text-xs font-bold text-on-surface uppercase tracking-wide">
            PROGNOSTICS VECTOR TIMELINE & REPLAY SCRUBBER
          </h3>
          <span className="font-label-micro text-[10px] text-outline hidden md:inline">
            // 1D-CNN GATED MODEL • TWO-STAGE INFERENCE
          </span>
        </div>

        {/* Playback Controls Inline */}
        <div className="flex items-center gap-2">
          <button 
            type="button"
            onClick={onTogglePlay}
            className="w-7 h-7 bg-primary text-on-primary rounded flex items-center justify-center hover:brightness-110 transition-all shadow-sm"
            title="Play / Pause Telemetry Playback"
          >
            <span className="material-symbols-outlined text-[16px]">
              {isPlaying ? "pause" : "play_arrow"}
            </span>
          </button>

          <div className="flex items-center bg-surface-container-high border border-outline-variant rounded font-label-code text-[11px] p-0.5">
            {[1, 5, 10].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSetSpeed(s)}
                className={`px-1.5 py-0.5 rounded transition-colors ${playbackSpeed === s ? 'text-primary font-bold bg-surface-container-highest' : 'text-outline hover:text-on-surface'}`}
              >
                {s}x
              </button>
            ))}
          </div>

          {tFirstDetected && (
            <button 
              type="button"
              onClick={onJumpToAnomaly}
              className="px-2 py-0.5 bg-tertiary/20 border border-tertiary/50 text-tertiary rounded font-label-code text-xs hover:bg-tertiary/30 transition-colors flex items-center gap-1 font-bold"
            >
              <span className="material-symbols-outlined text-[13px]">crisis_alert</span>
              JUMP TO ANOMALY
            </button>
          )}

          <div className="font-telemetry-data text-xs text-on-surface-variant bg-surface-container-high px-2 py-0.5 rounded border border-outline-variant/30 font-mono">
            <span className="text-outline">MET:</span> <span className="text-primary font-bold">{metStr}</span>
          </div>
        </div>
      </div>

      {/* SCADA TECHNICAL VECTOR CHART CONTAINER (Compact Height h-40) */}
      <div className="relative w-full h-40 bg-surface-container-lowest border border-outline-variant/30 rounded p-1 overflow-hidden">
        <svg className="w-full h-full" viewBox="0 0 900 160" preserveAspectRatio="none">
          <defs>
            <linearGradient id="divertZoneGrad" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#ffb4ab" stopOpacity="0.08" />
              <stop offset="100%" stopColor="#ffb4ab" stopOpacity="0.25" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1="40" y1="15" x2="880" y2="15" stroke="#3d494c" strokeWidth="0.5" strokeDasharray="2,3" />
          <line x1="40" y1="47" x2="880" y2="47" stroke="#3d494c" strokeWidth="0.5" strokeDasharray="2,3" />
          <line x1="40" y1="80" x2="880" y2="80" stroke="#3d494c" strokeWidth="0.5" strokeDasharray="2,3" />
          <line x1="40" y1="112" x2="880" y2="112" stroke="#3d494c" strokeWidth="0.5" strokeDasharray="2,3" />
          <line x1="40" y1="145" x2="880" y2="145" stroke="#3d494c" strokeWidth="0.5" strokeDasharray="2,3" />

          {/* Critical Zone (< 2.0h RUL) */}
          <rect x="40" y="112" width="840" height="33" fill="url(#divertZoneGrad)" />
          <line x1="40" y1="112" x2="880" y2="112" stroke="#ffb4ab" strokeWidth="1" strokeDasharray="4,3" />
          <text x="45" y="124" fill="#ffb4ab" fontFamily="JetBrains Mono" fontSize="9" fontWeight="700">
            CRITICAL DIVERT THRESHOLD (2.0h RUL)
          </text>

          {/* Y-Axis Labels */}
          <text x="34" y="18" fill="#869397" fontFamily="JetBrains Mono" fontSize="9" textAnchor="end">5.0h</text>
          <text x="34" y="50" fill="#869397" fontFamily="JetBrains Mono" fontSize="9" textAnchor="end">4.0h</text>
          <text x="34" y="83" fill="#869397" fontFamily="JetBrains Mono" fontSize="9" textAnchor="end">3.0h</text>
          <text x="34" y="115" fill="#869397" fontFamily="JetBrains Mono" fontSize="9" textAnchor="end">2.0h</text>
          <text x="34" y="148" fill="#869397" fontFamily="JetBrains Mono" fontSize="9" textAnchor="end">1.0h</text>

          {/* Historical RUL path */}
          {histPathD && (
            <path d={histPathD} fill="none" stroke="#4cd7f6" strokeWidth="2" strokeLinejoin="round" />
          )}

          {/* Projected RUL path */}
          {projPathD && (
            <path d={projPathD} fill="none" stroke="#ffb95f" strokeWidth="1.8" strokeDasharray="4,3" strokeLinecap="round" />
          )}

          {/* Anomaly Inception Line & Uncertainty Note */}
          {anomalyX && (
            <g>
              <line x1={anomalyX} y1="10" x2={anomalyX} y2="148" stroke="#ffb95f" strokeWidth="1" strokeDasharray="2,2" />
              <text x={anomalyX} y="22" fill="#ffb95f" fontFamily="JetBrains Mono" fontSize="8" fontWeight="700" textAnchor="middle">
                ANOMALY T+{tFirstDetected}s
              </text>
              <text x={Math.min(680, anomalyX + 8)} y="36" fill="#4cd7f6" fontFamily="JetBrains Mono" fontSize="7.5" fontStyle="italic">
                * Estimate uncertainty decreases as degradation evidence accumulates
              </text>
            </g>
          )}

          {/* Scrubber Cursor Needle */}
          <line x1={cursorX} y1="10" x2={cursorX} y2="148" stroke="#4cd7f6" strokeWidth="1.5" />
          <polygon points={`${cursorX-4},10 ${cursorX+4},10 ${cursorX},16`} fill="#4cd7f6" />
          <circle cx={cursorX} cy={cursorY} r="4" fill="#4cd7f6" stroke="#10131a" strokeWidth="1.5" />
        </svg>

        {/* Floating Telemetry Tooltip Overlay */}
        <div 
          className="absolute bg-surface-container-high/95 border border-primary px-2 py-1 rounded shadow-md pointer-events-none transform -translate-x-1/2"
          style={{ left: `${Math.min(92, Math.max(8, (cursorX / 900) * 100)).toFixed(1)}%`, top: "2rem" }}
        >
          <div className="font-telemetry-data text-xs text-on-surface font-bold whitespace-nowrap">
            RUL: <span className="text-tertiary">{frame?.rul?.formatted || "--"}</span>
          </div>
        </div>
      </div>

      {/* Interactive Timeline Range Scrubber Slider & Legend */}
      <div className="space-y-1">
        <input 
          type="range"
          min={0}
          max={numFrames - 1}
          value={currentIndex}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="w-full accent-primary bg-surface-container-high h-1.5 rounded cursor-ew-resize appearance-none"
        />
        <div className="flex justify-between items-center font-label-micro text-[10px] text-outline px-1">
          <span className="hover:text-on-surface cursor-pointer" onClick={() => onSeek(0)}>[TAKEOFF T+00]</span>
          <div className="flex items-center gap-3">
            <span className="text-primary flex items-center gap-1">
              <span className="w-2 h-0.5 bg-primary"></span> HISTORICAL RUL
            </span>
            <span className="text-tertiary flex items-center gap-1">
              <span className="w-2 h-0.5 bg-tertiary border-b stroke-dasharray"></span> PROJECTED TRAJECTORY
            </span>
            <span className="text-outline italic hidden lg:inline">
              (Estimate uncertainty decreases as degradation evidence accumulates)
            </span>
          </div>
          <span className="hover:text-on-surface cursor-pointer" onClick={() => onSeek(numFrames - 1)}>[END T+{numFrames - 1}s]</span>
        </div>
      </div>
    </section>
  );
}

