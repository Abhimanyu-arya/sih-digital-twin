import React from 'react';

const SENSOR_META = [
  { key: "rpm", label: "RPM", unit: "rpm", rangeLimit: "5,800 MAX" },
  { key: "cht_c", label: "CYL HEAD TEMP", unit: "°C", rangeLimit: "135°C LIMIT" },
  { key: "egt_c", label: "EXHAUST GAS", unit: "°C", rangeLimit: "880°C LIMIT" },
  { key: "oil_pressure_bar", label: "OIL PRESSURE", unit: "bar", rangeLimit: "2.0–5.0 BAR NOM" },
  { key: "oil_temp_c", label: "OIL TEMP", unit: "°C", rangeLimit: "130°C LIMIT" },
  { key: "vibration_g", label: "CRANKCASE VIB", unit: "g", rangeLimit: "0.50g LIMIT" },
  { key: "alternator_v", label: "ALT BUS VOLT", unit: "VDC", rangeLimit: "13.8V NOM" }
];

export default function SensorMatrix({ sensors }) {
  if (!sensors) return null;

  return (
    <section>
      <div className="flex items-center justify-between mb-unit-xs">
        <div className="flex items-center gap-unit-xs">
          <span className="material-symbols-outlined text-primary text-[16px]">sensors</span>
          <span className="font-headline-sm text-headline-sm uppercase text-on-surface">Sensor Telemetry Matrix</span>
          <span className="font-label-micro text-label-micro text-outline">// ROTAX 912 ULS SAMPLING AT 100Hz</span>
        </div>
        <span className="font-label-micro text-label-micro text-secondary flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span> 7 ACTIVE SENSOR CHANNELS
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-gutter-dense">
        {SENSOR_META.map((meta) => {
          const sData = sensors[meta.key] || {};
          const status = sData.status || "NOMINAL";
          const valNum = sData.value ?? "--";
          const pct = sData.pct ?? 50;

          let cardBorder = "border-outline-variant/40";
          let textVal = "text-on-surface";
          let badgeStyle = "text-secondary bg-secondary/10 border-secondary/30";
          let barBg = "bg-secondary";

          if (status === "CRITICAL") {
            cardBorder = "border-2 border-error shadow-[0_0_16px_rgba(255,180,171,0.25)] relative overflow-hidden";
            textVal = "text-error";
            badgeStyle = "text-error bg-error-container/40 border-error animate-pulse font-bold";
            barBg = "bg-error";
          } else if (status === "CAUTION") {
            cardBorder = "border-2 border-tertiary shadow-[0_0_12px_rgba(255,185,95,0.18)]";
            textVal = "text-tertiary";
            badgeStyle = "text-tertiary bg-tertiary/20 border-tertiary font-bold";
            barBg = "bg-tertiary";
          }

          return (
            <div 
              key={meta.key} 
              className={`bg-surface-container-low p-2.5 border ${cardBorder} rounded flex flex-col justify-between transition-all hover:bg-surface-container-high/80`}
              title={`${meta.label} Range Limit: ${meta.rangeLimit}`}
            >
              {status === "CRITICAL" && (
                <div className="absolute inset-0 bg-error/5 pointer-events-none animate-pulse"></div>
              )}

              {/* 1. Sensor Name & Status Color Dot */}
              <div className="flex items-center justify-between">
                <span className={`font-label-micro text-[11px] uppercase font-bold tracking-wide ${status === 'CRITICAL' ? 'text-error' : status === 'CAUTION' ? 'text-tertiary' : 'text-on-surface-variant'}`}>
                  {meta.label}
                </span>
                <span className={`w-2 h-2 rounded-full ${status === 'CRITICAL' ? 'bg-error animate-ping' : status === 'CAUTION' ? 'bg-tertiary' : 'bg-secondary'}`}></span>
              </div>

              {/* 2. Current Value + Unit (Prominent & Large) */}
              <div className="my-1.5 flex items-baseline justify-between">
                <div className="flex items-baseline gap-1">
                  <span className={`font-telemetry-data text-2xl font-extrabold ${textVal}`}>
                    {valNum}
                  </span>
                  <span className="font-telemetry-unit text-xs font-semibold text-on-surface-variant">
                    {meta.unit}
                  </span>
                </div>
              </div>

              {/* 3. Visual Level Bar */}
              <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden my-1">
                <div className={`${barBg} h-full transition-all duration-300`} style={{ width: `${pct}%` }}></div>
              </div>

              {/* 4. Subtle Single Line Footnote */}
              <div className="flex justify-between items-center text-[9px] font-mono text-outline pt-0.5">
                <span className={`px-1 rounded ${badgeStyle}`}>
                  {status}
                </span>
                <span className="truncate max-w-[80px] opacity-75">{meta.rangeLimit}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

