import React from 'react';
import { GitCommit, ArrowRight, ShieldCheck } from 'lucide-react';

interface ProvenanceChainProps {
  provenance: string[];
  className?: string;
}

export const ProvenanceChain: React.FC<ProvenanceChainProps> = ({
  provenance,
  className = '',
}) => {
  if (!provenance || provenance.length === 0) {
    return (
      <div className="text-xs text-slate-500 italic">No provenance recorded</div>
    );
  }

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
        <ShieldCheck className="w-3.5 h-3.5 text-ultrone-400" />
        <span>Provenance Chain</span>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {provenance.map((step, idx) => (
          <React.Fragment key={idx}>
            <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-xs font-mono text-slate-300">
              <GitCommit className="w-3 h-3 text-ultrone-400" />
              <span>{step}</span>
            </div>
            {idx < provenance.length - 1 && (
              <ArrowRight className="w-3 h-3 text-slate-600 shrink-0" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default ProvenanceChain;
