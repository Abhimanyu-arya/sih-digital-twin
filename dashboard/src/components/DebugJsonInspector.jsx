import React from 'react';

export default function DebugJsonInspector({ currentFrame, currentMission, onClose }) {
  if (!currentFrame) return null;

  return (
    <div className="bg-surface-container border-2 border-primary rounded p-unit-md shadow-2xl relative overflow-hidden font-telemetry-data text-xs">
      <div className="flex items-center justify-between pb-unit-xs mb-unit-xs border-b border-outline-variant/40">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[18px]">bug_report</span>
          <span className="font-bold text-primary tracking-wider uppercase">
            DEBUG DATA VERIFICATION // RAW SOURCE JSON INSPECTOR
          </span>
          <span className="text-on-surface-variant font-mono">
            [MISSION: {currentMission?.mission_id} | MET: {currentFrame.met_formatted} | TS: {currentFrame.timestamp}s]
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-on-surface-variant hover:text-error font-bold text-sm px-2 py-0.5 rounded bg-surface-container-high border border-outline-variant"
        >
          ✕ CLOSE
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-unit-md max-h-96 overflow-y-auto">
        {/* Left Column: System Status & RUL Raw */}
        <div className="space-y-unit-xs bg-surface-container-lowest p-unit-xs rounded border border-outline-variant/30">
          <h5 className="text-secondary font-bold uppercase tracking-widest text-[11px] border-b border-outline-variant/20 pb-0.5">
            1. SYSTEM STATUS & RUL PAYLOAD
          </h5>
          <table className="w-full text-left font-mono">
            <tbody>
              <tr className="border-b border-outline-variant/20">
                <td className="text-outline py-0.5">system_status.state</td>
                <td className="text-primary font-bold">{currentFrame.system_status?.state}</td>
              </tr>
              <tr className="border-b border-outline-variant/20">
                <td className="text-outline py-0.5">system_status.level</td>
                <td className="text-on-surface">{currentFrame.system_status?.level}</td>
              </tr>
              <tr className="border-b border-outline-variant/20">
                <td className="text-outline py-0.5">system_status.message</td>
                <td className="text-on-surface">{currentFrame.system_status?.message}</td>
              </tr>
              <tr className="border-b border-outline-variant/20">
                <td className="text-outline py-0.5">rul.seconds</td>
                <td className="text-tertiary font-bold">{currentFrame.rul?.seconds ?? "null"}</td>
              </tr>
              <tr className="border-b border-outline-variant/20">
                <td className="text-outline py-0.5">rul.formatted</td>
                <td className="text-tertiary">{currentFrame.rul?.formatted}</td>
              </tr>
              <tr className="border-b border-outline-variant/20">
                <td className="text-outline py-0.5">rul.ci_lower_h / upper_h</td>
                <td className="text-on-surface-variant">[{currentFrame.rul?.ci_lower_h}h — {currentFrame.rul?.ci_upper_h}h]</td>
              </tr>
              <tr>
                <td className="text-outline py-0.5">anomaly_inception_s</td>
                <td className="text-on-surface">{currentFrame.system_status?.anomaly_inception_s}s</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Right Column: Sensors Raw Breakdown */}
        <div className="space-y-unit-xs bg-surface-container-lowest p-unit-xs rounded border border-outline-variant/30">
          <h5 className="text-secondary font-bold uppercase tracking-widest text-[11px] border-b border-outline-variant/20 pb-0.5">
            2. RAW SENSOR CHANNELS (7 SENSORS)
          </h5>
          <table className="w-full text-left font-mono">
            <thead>
              <tr className="text-outline border-b border-outline-variant/30 text-[10px]">
                <th className="py-0.5">CHANNEL</th>
                <th className="py-0.5">VALUE</th>
                <th className="py-0.5">STATUS</th>
                <th className="py-0.5">PCT</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(currentFrame.sensors || {}).map(([ch, data]) => (
                <tr key={ch} className="border-b border-outline-variant/10 text-[11px]">
                  <td className="text-outline py-0.5">{ch}</td>
                  <td className="text-on-surface font-bold">{data.value} ({data.display_value})</td>
                  <td className={data.status === 'CRITICAL' ? 'text-error font-bold' : data.status === 'CAUTION' ? 'text-tertiary font-bold' : 'text-secondary'}>
                    {data.status}
                  </td>
                  <td className="text-on-surface-variant">{data.pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Bottom Full Row: SHAP Factors Raw */}
        <div className="md:col-span-2 space-y-unit-xs bg-surface-container-lowest p-unit-xs rounded border border-outline-variant/30">
          <h5 className="text-secondary font-bold uppercase tracking-widest text-[11px] border-b border-outline-variant/20 pb-0.5">
            3. RAW SHAP EXPLAINABILITY FACTORS ({currentFrame.shap_factors?.length || 0} ITEMS)
          </h5>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {currentFrame.shap_factors?.map((f) => (
              <div key={f.rank} className="p-2 bg-surface-container-high rounded border border-outline-variant/20 space-y-1">
                <div className="flex justify-between items-center text-[10px] font-bold text-tertiary">
                  <span>RANK #{f.rank} [{f.weight_pct}% WEIGHT]</span>
                  <span className="text-on-surface-variant">{f.severity}</span>
                </div>
                <div className="font-bold text-on-surface text-[11px]">{f.title}</div>
                <div className="text-outline text-[10px]">{f.feature_raw} = {f.value_str}</div>
                <div className="text-on-surface-variant text-[10px] italic">{f.description}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
