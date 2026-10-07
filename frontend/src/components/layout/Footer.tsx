import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto border-t border-ash/80 bg-canvas py-10 text-xs text-slate">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          
          {/* Col 1: System info */}
          <div className="space-y-1">
            <p className="font-display text-lg font-black uppercase tracking-tight text-carbon">
              AUTHENTICA
            </p>
            <p className="text-[12px] text-slate">
              AI media manipulation analysis &amp; social-engineering fraud protection.
            </p>
          </div>

          {/* Col 2: Engine specs */}
          <div className="flex flex-wrap items-center gap-2 justify-start md:justify-center font-mono text-[10px]">
            <span className="px-2.5 py-1 rounded-pill bg-paper border border-ash text-carbon font-semibold">
              EFFNET-B0 · AASIST · WHISPER
            </span>
            <span className="px-2.5 py-1 rounded-pill bg-paper border border-ash text-carbon font-semibold">
              C2PA PROVENANCE
            </span>
          </div>

          {/* Col 3: Disclaimer & Privacy */}
          <div className="text-left md:text-right text-[11px] text-slate space-y-0.5 font-mono">
            <p className="text-carbon font-medium">
              Zero Data Retention · Local Ephemeral Ingestion
            </p>
            <p className="text-smoke">
              Forensic model scores indicate benchmark activations, not proof.
            </p>
          </div>

        </div>
      </div>
    </footer>
  );
};
