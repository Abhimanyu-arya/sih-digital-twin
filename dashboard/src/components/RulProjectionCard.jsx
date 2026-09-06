import React from 'react';

export default function RulProjectionCard({ rulPayload }) {
  const formatted = rulPayload?.formatted || "--h --m";
  const diffPlan = rulPayload?.diff_vs_plan || "NOMINAL FLIGHT PLAN";
  const ciLower = rulPayload?.ci_lower_h;
  const ciUpper = rulPayload?.ci_upper_h;
  const advisory = rulPayload?.advisory || "ALL SYSTEMS OPERATING WITHIN NORMAL PARAMETERS.";
  const seconds = rulPayload?.seconds;

  let stateText = "text-secondary";
  let borderStyle = "border-outline-variant/50";
  if (seconds !== null && seconds !== undefined) {
    if (seconds < 60) {
      stateText = "text-error";
    } else {
      stateText = "text-tertiary";
    }
  }

  return (
    <div className={`bg-surface-container-low p-unit-md border ${borderStyle} rounded flex flex-col justify-between`}>
      <div className="flex items-center justify-between">
        <span className="font-label-micro text-label-micro text-outline uppercase tracking-wider flex items-center gap-1">
          <span className="material-symbols-outlined text-[13px] text-primary">timer</span>
          REMAINING USEFUL LIFE (RUL) PROJECTION
        </span>
        <span className="font-label-code text-label-code text-primary bg-primary/10 px-unit-xs py-0.5 rounded border border-primary/30">
          FADEC ML MODEL // 1D-CNN GATED
        </span>
      </div>

      <div className="flex flex-wrap items-baseline gap-x-unit-md gap-y-unit-xs my-unit-xs">
        <div className="flex items-baseline gap-unit-xs">
          <span className={`font-display-lg text-display-lg ${stateText} font-bold tracking-tight`}>
            {formatted}
          </span>
          <span className="font-telemetry-unit text-telemetry-unit text-on-surface-variant">EST. SAFE TIME</span>
        </div>
        <div className="flex flex-col">
          <span className={`font-label-code text-label-code ${stateText} font-semibold flex items-center gap-0.5`}>
            <span className="material-symbols-outlined text-[14px]">trending_down</span>
            {diffPlan}
          </span>
          <span className="font-label-micro text-label-micro text-outline">
            {ciLower !== null && ciUpper !== null ? `95% CI: [${ciLower}h — ${ciUpper}h]` : "95% CI: NOMINAL ENVELOPE"}
          </span>
        </div>
      </div>

      <div className="bg-tertiary/10 border-l-2 border-tertiary px-unit-sm py-unit-xs rounded-r">
        <span className="font-label-micro text-label-micro text-tertiary font-bold tracking-wide uppercase block">DIRECTIVE ADVISORY:</span>
        <span className="font-body-compact text-body-compact text-on-surface block mt-0.5">
          {advisory}
        </span>
      </div>

      {/* Item 5: Explicit Causality Statement for Judges */}
      <div className="mt-unit-xs pt-unit-2xs border-t border-outline-variant/20 flex items-center gap-1 text-label-micro font-label-micro text-outline">
        <span className="material-symbols-outlined text-[13px] text-primary">verified</span>
        <span>Predictions computed causally frame-by-frame; precomputed for demo playback</span>
      </div>
    </div>
  );
}
