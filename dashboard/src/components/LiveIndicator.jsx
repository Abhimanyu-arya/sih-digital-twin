import React from 'react';

/**
 * LiveIndicator — Pulsing "LIVE" badge shown when streaming mode is active.
 */
export default function LiveIndicator({ isStreaming, isConnected }) {
  if (!isConnected) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-outline-variant/40 bg-surface-container-low">
        <span className="w-2 h-2 rounded-full bg-outline-variant" />
        <span className="font-label-micro text-[10px] text-outline-variant uppercase tracking-wider">
          OFFLINE
        </span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded border ${
      isStreaming 
        ? 'border-error/60 bg-error/10' 
        : 'border-secondary/40 bg-secondary/10'
    }`}>
      <span className={`w-2 h-2 rounded-full ${
        isStreaming ? 'bg-error animate-pulse' : 'bg-secondary'
      }`} />
      <span className={`font-label-micro text-[10px] uppercase tracking-wider font-bold ${
        isStreaming ? 'text-error' : 'text-secondary'
      }`}>
        {isStreaming ? 'LIVE' : 'READY'}
      </span>
    </div>
  );
}
