import React from 'react';
import { 
  Layers, Scale, Zap, ShieldAlert, Lock, Database, 
  Cpu, GitBranch, Terminal, HelpCircle, CheckCircle2, Sparkles, Activity, FileCode, Compass
} from 'lucide-react';

interface DepthMeterProps {
  currentDimension?: string;
  depthDimension?: string;
  currentDepth?: number;
  phase?: string;
  currentItemTitle?: string;
  currentItemType?: string;
  isClarification?: boolean;
  previousEval?: {
    quality_band?: string;
    earned_points?: number;
    possible_points?: number;
    severity?: string;
    feedback?: string;
    is_clarification_prompt?: boolean;
    is_scored?: boolean;
    evidence_score?: number;
    concise_evaluation_summary?: string;
  };
}

const DIMENSION_CONFIG: Record<string, { label: string; description: string; icon: React.FC<{ className?: string }> }> = {
  architecture: {
    label: 'System Architecture',
    description: 'Component boundaries, modularity, and structural design choices.',
    icon: Cpu
  },
  implementation: {
    label: 'Implementation Details',
    description: 'Concrete code mechanics, algorithms, data structures, and APIs.',
    icon: FileCode
  },
  reasoning: {
    label: 'Design Rationale',
    description: 'Technical justification, engineering intent, and design choices.',
    icon: Compass
  },
  tradeoff: {
    label: 'Trade-off Analysis',
    description: 'Comparing alternatives, operational costs, and deliberate compromises.',
    icon: Scale
  },
  scale: {
    label: 'Scale & Performance',
    description: 'High throughput, latency optimization, caching, and bottlenecks.',
    icon: Zap
  },
  failure: {
    label: 'Resilience & Recovery',
    description: 'Fault isolation, circuit breakers, fallback semantics, and error handling.',
    icon: ShieldAlert
  },
  security: {
    label: 'Security & Threat Modeling',
    description: 'Authentication, authorization, data protection, and attack surface defense.',
    icon: Lock
  },
  concurrency: {
    label: 'Concurrency & Synchronization',
    description: 'Thread safety, race conditions, deadlocks, and asynchronous flows.',
    icon: GitBranch
  },
  consistency: {
    label: 'Distributed Consistency',
    description: 'ACID guarantees, consensus, replication, and distributed state.',
    icon: Database
  },
  operations: {
    label: 'Operational Reliability',
    description: 'Observability, telemetry, monitoring, and release engineering.',
    icon: Activity
  },
  debugging: {
    label: 'Root-Cause Debugging',
    description: 'Diagnostic methodology, profiling, and incident resolution.',
    icon: Terminal
  },
  responsibilities: {
    label: 'Role Responsibilities',
    description: 'Production ownership, architectural scope, and personal impact.',
    icon: Layers
  }
};

const PRIMARY_DIMENSIONS = [
  { key: 'architecture', label: 'Architecture' },
  { key: 'implementation', label: 'Implementation' },
  { key: 'tradeoff', label: 'Trade-offs' },
  { key: 'scale', label: 'Scale' },
  { key: 'failure', label: 'Resilience' },
  { key: 'concurrency', label: 'Concurrency' },
  { key: 'consistency', label: 'Consistency' },
  { key: 'security', label: 'Security' }
];

function resolveDimension(rawDim?: string): { key: string; label: string; description: string; Icon: React.FC<{ className?: string }> } {
  const norm = (rawDim || 'architecture').toLowerCase().replace(/[_-]/g, ' ');
  
  if (norm.includes('trade')) {
    return { key: 'tradeoff', ...DIMENSION_CONFIG.tradeoff, Icon: DIMENSION_CONFIG.tradeoff.icon };
  }
  if (norm.includes('scale') || norm.includes('perf')) {
    return { key: 'scale', ...DIMENSION_CONFIG.scale, Icon: DIMENSION_CONFIG.scale.icon };
  }
  if (norm.includes('fail') || norm.includes('resil') || norm.includes('recover')) {
    return { key: 'failure', ...DIMENSION_CONFIG.failure, Icon: DIMENSION_CONFIG.failure.icon };
  }
  if (norm.includes('secur') || norm.includes('auth')) {
    return { key: 'security', ...DIMENSION_CONFIG.security, Icon: DIMENSION_CONFIG.security.icon };
  }
  if (norm.includes('concurr') || norm.includes('thread') || norm.includes('sync') || norm.includes('lock')) {
    return { key: 'concurrency', ...DIMENSION_CONFIG.concurrency, Icon: DIMENSION_CONFIG.concurrency.icon };
  }
  if (norm.includes('consist') || norm.includes('acid') || norm.includes('transact')) {
    return { key: 'consistency', ...DIMENSION_CONFIG.consistency, Icon: DIMENSION_CONFIG.consistency.icon };
  }
  if (norm.includes('debug') || norm.includes('troubl') || norm.includes('diag')) {
    return { key: 'debugging', ...DIMENSION_CONFIG.debugging, Icon: DIMENSION_CONFIG.debugging.icon };
  }
  if (norm.includes('impl') || norm.includes('code')) {
    return { key: 'implementation', ...DIMENSION_CONFIG.implementation, Icon: DIMENSION_CONFIG.implementation.icon };
  }
  if (norm.includes('reason') || norm.includes('why') || norm.includes('justif')) {
    return { key: 'reasoning', ...DIMENSION_CONFIG.reasoning, Icon: DIMENSION_CONFIG.reasoning.icon };
  }
  if (norm.includes('operat') || norm.includes('monit') || norm.includes('observ')) {
    return { key: 'operations', ...DIMENSION_CONFIG.operations, Icon: DIMENSION_CONFIG.operations.icon };
  }
  if (norm.includes('respon') || norm.includes('owner') || norm.includes('role')) {
    return { key: 'responsibilities', ...DIMENSION_CONFIG.responsibilities, Icon: DIMENSION_CONFIG.responsibilities.icon };
  }
  if (norm.includes('arch') || norm.includes('struct') || norm.includes('design')) {
    return { key: 'architecture', ...DIMENSION_CONFIG.architecture, Icon: DIMENSION_CONFIG.architecture.icon };
  }

  // Fallback to direct key or generic
  const direct = DIMENSION_CONFIG[norm];
  if (direct) {
    return { key: norm, ...direct, Icon: direct.icon };
  }

  return {
    key: norm,
    label: norm.charAt(0).toUpperCase() + norm.slice(1),
    description: 'Testing technical engineering depth and problem-solving rationale.',
    Icon: Layers
  };
}

export const DepthMeter: React.FC<DepthMeterProps> = ({
  currentDimension,
  depthDimension,
  currentDepth,
  phase,
  currentItemTitle,
  currentItemType,
  isClarification,
  previousEval
}) => {
  const activeDim = resolveDimension(currentDimension || depthDimension);
  const DimensionIcon = activeDim.Icon;
  const isClarificationActive = isClarification || previousEval?.is_clarification_prompt || previousEval?.is_scored === false;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
      {/* Top Header: Exploration Dimension */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Exploration Dimension
          </span>
        </div>
        <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 font-semibold">
          {activeDim.label}
        </span>
      </div>

      {/* Active Dimension Focus Card */}
      <div className="p-3.5 rounded-xl bg-slate-950/90 border border-slate-800/90 space-y-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center shrink-0">
            <DimensionIcon className="w-4 h-4 text-indigo-300" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-bold text-white truncate">
              {activeDim.label}
            </div>
            {currentItemTitle && (
              <div className="text-[10px] text-slate-400 truncate">
                Item: <span className="text-slate-200 font-medium">{currentItemTitle}</span>
              </div>
            )}
          </div>
        </div>

        <p className="text-[11px] text-slate-400 leading-relaxed">
          {activeDim.description}
        </p>
      </div>

      {/* Dimension Spectrum Indicator */}
      <div className="space-y-1.5">
        <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-500">
          Exploration Spectrum
        </div>
        <div className="flex flex-wrap gap-1.5">
          {PRIMARY_DIMENSIONS.map((dim) => {
            const isActive = dim.key === activeDim.key;
            return (
              <span
                key={dim.key}
                className={`text-[10px] px-2 py-0.5 rounded-md font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white font-semibold shadow-sm shadow-indigo-600/40 border border-indigo-400/50'
                    : 'bg-slate-950 text-slate-400 border border-slate-800/80'
                }`}
              >
                {dim.label}
              </span>
            );
          })}
        </div>
      </div>

      {/* Meaningful Context Note */}
      <div className="text-[10px] text-slate-400 italic leading-relaxed border-t border-slate-800/60 pt-2">
        Depth describes the kind of reasoning being tested; it does not by itself determine score or when the interview ends.
      </div>

      {/* Evaluated Turn Feedback & Prominent Score Display */}
      {previousEval && (
        <div className={`pt-3 border-t text-xs ${isClarificationActive ? 'border-amber-800/60 bg-amber-950/20 -mx-4 sm:-mx-5 -mb-4 sm:-mb-5 p-4 rounded-b-2xl' : 'border-slate-800/80'}`}>
          <div className="flex items-center justify-between mb-1.5 gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 text-[11px]">Evaluation:</span>
              <span
                className={`font-semibold px-2 py-0.5 rounded text-[10px] ${
                  isClarificationActive
                    ? 'bg-amber-950 text-amber-300 border border-amber-700 font-bold'
                    : 'bg-indigo-950 text-indigo-300 border border-indigo-800 font-medium'
                }`}
              >
                {isClarificationActive ? (
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    Clarification requested
                  </span>
                ) : previousEval.evidence_score != null ? (
                  `${Math.round(previousEval.evidence_score * 100)}% Evidence`
                ) : (
                  previousEval.quality_band || 'Turn Evaluated'
                )}
              </span>
            </div>

            {/* Prominent Earned / Possible Points Display */}
            {isClarificationActive ? (
              <span className="text-amber-400 font-medium text-[11px]">
                Unscored Inquiry
              </span>
            ) : (
              <span className="font-mono text-emerald-400 font-bold text-xs bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/40">
                +{Number(previousEval.earned_points || 0).toFixed(1)} / {Number(previousEval.possible_points || 0).toFixed(1)} pts
              </span>
            )}
          </div>

          {(previousEval.feedback || previousEval.concise_evaluation_summary) && (
            <p className="text-slate-300 italic text-[11px] line-clamp-2 mt-1">
              "{previousEval.feedback || previousEval.concise_evaluation_summary}"
            </p>
          )}
        </div>
      )}
    </div>
  );
};

