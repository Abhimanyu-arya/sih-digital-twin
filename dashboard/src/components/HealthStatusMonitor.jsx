import React from 'react';

export default function HealthStatusMonitor({ systemStatus, sensors }) {
  const state = systemStatus?.state || "NOMINAL";
  const level = systemStatus?.level || "LVL 1 NOMINAL";
  const msg = systemStatus?.message || "NOMINAL";
  const inception = systemStatus?.anomaly_inception_s ?? 0;
  const persistence = systemStatus?.persistence_s ?? 0;

  // State styling
  let cardBorder = "border-secondary/60";
  let textAccent = "text-secondary";
  let bgGlow = "bg-secondary/10";
  let badgeStyle = "text-secondary bg-secondary/20 border-secondary/40";
  let iconName = "check_circle";

  if (state === "CRITICAL") {
    cardBorder = "border-error border-2";
    textAccent = "text-error";
    bgGlow = "bg-error/10";
    badgeStyle = "text-error bg-error/20 border-error/40";
    iconName = "emergency";
  } else if (state === "DEGRADED") {
    cardBorder = "border-tertiary/70 border-2";
    textAccent = "text-tertiary";
    bgGlow = "bg-tertiary/10";
    badgeStyle = "text-tertiary bg-tertiary/20 border-tertiary/40";
    iconName = "warning";
  }

  const oilP = sensors?.oil_pressure_bar;
  const vib = sensors?.vibration_g;
  const oilT = sensors?.oil_temp_c;

  const persMins = Math.floor(persistence / 60);
  const persSecs = persistence % 60;

  return (
    <div className={`bg-surface-container-low p-unit-md ${cardBorder} rounded flex flex-col justify-between relative overflow-hidden transition-all duration-300`}>
      <div className={`absolute -right-8 -top-8 w-28 h-28 ${bgGlow} rounded-full blur-xl pointer-events-none`}></div>
      <div className="flex items-start justify-between">
        <div className="flex flex-col">
          <span className={`font-label-micro text-label-micro ${textAccent} tracking-widest uppercase flex items-center gap-1.5`}>
            <span className={`material-symbols-outlined text-[14px] ${textAccent}`}>{iconName}</span>
            HEALTH STATUS MONITOR
          </span>
          <div className={`font-headline-lg text-headline-lg ${textAccent} uppercase mt-1 tracking-wider flex items-center gap-2`}>
            <span className={`w-2.5 h-2.5 rounded-full ${state === 'NOMINAL' ? 'bg-secondary' : state === 'DEGRADED' ? 'bg-tertiary animate-ping' : 'bg-error animate-ping'}`}></span>
            {msg}
          </div>
        </div>
        <span className={`font-label-code text-label-code ${badgeStyle} px-unit-xs py-0.5 rounded border`}>
          {level}
        </span>
      </div>

      {/* Quick Sub-status Metrics Array */}
      <div className="grid grid-cols-3 gap-unit-xs my-unit-sm pt-unit-xs border-t border-outline-variant/30">
        <div className="bg-surface-container-high/60 p-unit-xs rounded">
          <span className="font-label-micro text-label-micro text-outline block">OIL PRESSURE</span>
          <span className={`font-telemetry-data text-telemetry-data font-bold block mt-0.5 ${oilP?.status === 'CRITICAL' ? 'text-error' : oilP?.status === 'CAUTION' ? 'text-tertiary' : 'text-secondary'}`}>
            {oilP?.display_value || "3.50"} bar
          </span>
          <span className="font-label-micro text-label-micro text-outline">2.0–5.0 BAR NOM</span>
        </div>
        <div className="bg-surface-container-high/60 p-unit-xs rounded">
          <span className="font-label-micro text-label-micro text-outline block">CRANKCASE VIB</span>
          <span className={`font-telemetry-data text-telemetry-data font-bold block mt-0.5 ${vib?.status === 'CRITICAL' ? 'text-error' : vib?.status === 'CAUTION' ? 'text-tertiary' : 'text-secondary'}`}>
            {vib?.display_value || "0.22"} g
          </span>
          <span className="font-label-micro text-label-micro text-outline">LIMIT: 0.50 g</span>
        </div>
        <div className="bg-surface-container-high/60 p-unit-xs rounded">
          <span className="font-label-micro text-label-micro text-outline block">OIL SUMP TEMP</span>
          <span className={`font-telemetry-data text-telemetry-data font-bold block mt-0.5 ${oilT?.status === 'CRITICAL' ? 'text-error' : oilT?.status === 'CAUTION' ? 'text-tertiary' : 'text-secondary'}`}>
            {oilT?.display_value || "98.0°C"}
          </span>
          <span className="font-label-micro text-label-micro text-outline">LIMIT: 130°C</span>
        </div>
      </div>

      <div className="flex items-center justify-between font-label-micro text-label-micro text-outline pt-unit-2xs border-t border-outline-variant/20">
        <span>ANOMALY INCEPTION: T+{Math.floor(inception/60).toString().padStart(2, '0')}:{(inception%60).toString().padStart(2, '0')}</span>
        <span className={textAccent}>PERSISTENCE: {persMins}m {persSecs}s</span>
      </div>
    </div>
  );
}
