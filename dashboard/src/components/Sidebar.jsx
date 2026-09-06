import React from 'react';

export default function Sidebar() {
  return (
    <aside className="w-64 bg-surface-container-lowest border-r border-outline-variant/30 flex-none flex flex-col justify-between hidden md:flex h-full">
      <div className="p-4 space-y-3">
        <div className="pb-2 border-b border-outline-variant/20 flex items-center justify-between">
          <span className="font-label-micro text-label-micro text-outline uppercase tracking-widest">
            Subsystems Diagnostics
          </span>
          <span className="font-label-micro text-label-micro text-secondary font-bold">ONLINE</span>
        </div>
        <nav className="flex flex-col gap-1.5">
          {/* Active View */}
          <a className="flex items-center justify-between px-3 py-2 rounded transition-colors bg-primary-container text-on-primary-container font-bold" href="#">
            <span className="font-label-code text-label-code text-xs">01 // SYSTEM OVERVIEW</span>
            <span className="font-label-micro text-label-micro bg-primary/20 text-on-primary-container px-1 rounded text-[9px]">ACTIVE</span>
          </a>

          {/* Visually Disabled Non-Functional Subsystem Views */}
          <div className="flex items-center justify-between px-3 py-2 rounded text-on-surface-variant/40 opacity-40 cursor-not-allowed border border-transparent" title="Subsystem view not implemented in demo build">
            <span className="font-label-code text-label-code text-xs">02 // PISTON ENGINE CORE</span>
            <span className="font-label-micro text-label-micro border border-outline-variant/40 px-1 rounded text-[9px]">N/A</span>
          </div>

          <div className="flex items-center justify-between px-3 py-2 rounded text-on-surface-variant/40 opacity-40 cursor-not-allowed border border-transparent" title="Subsystem view not implemented in demo build">
            <span className="font-label-code text-label-code text-xs">03 // OIL & THERMAL LOOP</span>
            <span className="font-label-micro text-label-micro border border-outline-variant/40 px-1 rounded text-[9px]">N/A</span>
          </div>

          <div className="flex items-center justify-between px-3 py-2 rounded text-on-surface-variant/40 opacity-40 cursor-not-allowed border border-transparent" title="Subsystem view not implemented in demo build">
            <span className="font-label-code text-label-code text-xs">04 // FUEL FEED SYSTEM</span>
            <span className="font-label-micro text-label-micro border border-outline-variant/40 px-1 rounded text-[9px]">N/A</span>
          </div>

          <div className="flex items-center justify-between px-3 py-2 rounded text-on-surface-variant/40 opacity-40 cursor-not-allowed border border-transparent" title="Subsystem view not implemented in demo build">
            <span className="font-label-code text-label-code text-xs">05 // FADEC & COMM BUS</span>
            <span className="font-label-micro text-label-micro border border-outline-variant/40 px-1 rounded text-[9px]">N/A</span>
          </div>

          <div className="flex items-center justify-between px-3 py-2 rounded text-on-surface-variant/40 opacity-40 cursor-not-allowed border border-transparent" title="Subsystem view not implemented in demo build">
            <span className="font-label-code text-label-code text-xs">06 // FAULT MATRIX & LOGS</span>
            <span className="font-label-micro text-label-micro border border-outline-variant/40 px-1 rounded text-[9px]">N/A</span>
          </div>
        </nav>
      </div>

      <div className="p-4 border-t border-outline-variant/30 bg-surface-container-low">
        <div className="flex items-center justify-between mb-1">
          <span className="font-label-micro text-label-micro text-outline">GCS NODE ID</span>
          <span className="font-label-code text-label-code text-on-surface text-xs">CREECH-GCS-04</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="font-label-micro text-label-micro text-outline">SECURITY LEVEL</span>
          <span className="font-label-micro text-label-micro text-secondary-fixed-dim border border-secondary/30 bg-secondary/10 px-1 py-0.5 rounded uppercase text-[9px]">DEMO BUILD // UNCLASSIFIED</span>
        </div>
      </div>
    </aside>
  );
}
