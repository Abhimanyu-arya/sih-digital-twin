import React, { useState } from 'react';

export default function DiagnosticInferenceEngine({ shapFactors, faultLabel }) {
  const [showMore, setShowMore] = useState(false);

  if (!shapFactors || shapFactors.length === 0) return null;

  const topFactor = shapFactors.find(f => f.rank === 1) || shapFactors[0];
  const remainingFactors = shapFactors.filter(f => f.rank > 1);

  return (
    <section className="bg-surface-container-low border border-tertiary/60 rounded p-3 transition-all duration-300">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-tertiary text-[18px]">account_tree</span>
          <div>
            <div className="font-headline-sm text-xs text-on-surface flex items-center gap-2 font-bold uppercase">
              <span>DIAGNOSTIC INFERENCE ENGINE // TOP CONTRIBUTING FACTOR</span>
              <span className="font-label-micro text-[10px] bg-tertiary/20 text-tertiary border border-tertiary/40 px-1.5 py-0.5 rounded">
                SHAP EXPLAINABILITY
              </span>
            </div>
            <span className="font-label-micro text-[10px] text-outline">
              GRADIENT EXPLAINER • NEURAL RESIDUAL DETECTOR • {faultLabel || "ENGINE CORE"}
            </span>
          </div>
        </div>

        {remainingFactors.length > 0 && (
          <button 
            type="button"
            onClick={() => setShowMore(!showMore)}
            className="px-2.5 py-1 bg-surface-container-high border border-outline-variant hover:border-tertiary rounded text-xs font-label-code text-tertiary transition-all flex items-center gap-1 font-semibold"
          >
            <span>{showMore ? "HIDE ADDITIONAL FACTORS" : `SHOW MORE FACTORS (+${remainingFactors.length})`}</span>
            <span className="material-symbols-outlined text-[16px]">
              {showMore ? "expand_less" : "expand_more"}
            </span>
          </button>
        )}
      </div>

      {/* #1 Primary Factor (Expanded by default) */}
      {topFactor && (
        <div className="bg-surface-container-high/70 border-l-4 border-error p-3 rounded-r flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1 max-w-3xl">
            <div className="flex items-center gap-2">
              <span className="font-label-code text-xs text-error font-bold">
                #{topFactor.rank} [{topFactor.weight_pct}% WEIGHT — PRIMARY FACTOR]
              </span>
              <span className="font-label-micro text-[10px] bg-error/20 text-error px-1.5 py-0.5 rounded font-bold">
                {topFactor.severity}
              </span>
            </div>
            <h4 className="font-headline-sm text-sm text-on-surface font-bold">
              {topFactor.title}
            </h4>
            <p className="font-body-compact text-xs text-on-surface-variant leading-relaxed">
              {topFactor.description}
            </p>
          </div>
          <div className="flex flex-col items-start md:items-end font-telemetry-data text-right flex-none">
            <span className="text-error font-bold text-sm">{topFactor.value_str}</span>
            <span className="font-label-micro text-[10px] text-outline mt-0.5">
              SHAP CORRELATION: <strong className="text-on-surface">{topFactor.correlation}</strong>
            </span>
          </div>
        </div>
      )}

      {/* Collapsible Factors #2 and #3 */}
      {showMore && remainingFactors.length > 0 && (
        <div className="mt-2 space-y-2 pt-2 border-t border-outline-variant/30">
          {remainingFactors.map((factor) => {
            const isRank2 = factor.rank === 2;
            const borderColor = isRank2 ? "border-tertiary" : "border-outline-variant";
            const textColor = isRank2 ? "text-tertiary" : "text-outline";
            const badgeBg = isRank2 ? "bg-tertiary/20 text-tertiary" : "bg-surface-container-highest text-on-surface-variant";

            return (
              <div 
                key={factor.rank}
                className={`bg-surface-container-high/40 border-l-4 ${borderColor} p-2.5 rounded-r flex flex-col md:flex-row md:items-center justify-between gap-2`}
              >
                <div className="space-y-0.5 max-w-3xl">
                  <div className="flex items-center gap-2">
                    <span className={`font-label-code text-xs ${textColor} font-bold`}>
                      #{factor.rank} [{factor.weight_pct}% WEIGHT — {isRank2 ? 'SECONDARY' : 'CONTRIBUTING'}]
                    </span>
                    <span className={`font-label-micro text-[10px] ${badgeBg} px-1.5 py-0.5 rounded`}>
                      {factor.severity}
                    </span>
                  </div>
                  <h5 className="font-headline-sm text-xs text-on-surface font-semibold">
                    {factor.title}
                  </h5>
                  <p className="font-body-compact text-[11px] text-on-surface-variant">
                    {factor.description}
                  </p>
                </div>
                <div className="flex flex-col items-start md:items-end font-telemetry-data text-right flex-none">
                  <span className={`${textColor} font-bold text-xs`}>{factor.value_str}</span>
                  <span className="font-label-micro text-[10px] text-outline">
                    CORRELATION: {factor.correlation}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

