import React from 'react';
import { ShieldAlert, ArrowDownRight, Award, Zap } from 'lucide-react';

interface DepthMeterProps {
  currentDepth: number;
  maxDepth?: number;
  phase: string;
  previousEval?: {
    quality_band: string;
    earned_points: number;
    possible_points: number;
    severity: string;
    feedback: string;
    is_clarification_prompt?: boolean;
  };
}

export const DepthMeter: React.FC<DepthMeterProps> = ({
  currentDepth,
  maxDepth = 5,
  phase,
  previousEval
}) => {
  const isClarification = previousEval?.is_clarification_prompt || previousEval?.quality_band === 'Specification Clarification';

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Adaptive Follow-up Depth
          </span>
        </div>
        <span className="text-xs font-mono px-2 py-0.5 rounded bg-brand-950/80 text-brand-300 border border-brand-800/60 font-semibold">
          Level {currentDepth} of {maxDepth}
        </span>
      </div>

      {/* Progress Bars */}
      <div className="grid grid-cols-5 gap-1.5 mb-3">
        {Array.from({ length: maxDepth }).map((_, idx) => {
          const stepLevel = idx + 1;
          const isReached = stepLevel <= currentDepth;
          const isCurrent = stepLevel === currentDepth;

          return (
            <div key={idx} className="flex flex-col items-center gap-1">
              <div
                className={`w-full h-2 rounded-full transition-all duration-300 ${
                  isCurrent
                    ? 'bg-amber-400 shadow-sm shadow-amber-400/50 scale-105'
                    : isReached
                    ? 'bg-brand-500'
                    : 'bg-slate-800'
                }`}
              />
              <span className={`text-[10px] font-mono ${isCurrent ? 'text-amber-300 font-bold' : isReached ? 'text-brand-300' : 'text-slate-600'}`}>
                L{stepLevel}
              </span>
            </div>
          );
        })}
      </div>

      {/* Evaluator Evidence / Previous Turn Callout */}
      {previousEval && (
        <div className={`mt-3 pt-3 border-t text-xs ${isClarification ? 'border-amber-800/60 bg-amber-950/20 -mx-4 -mb-4 p-3 rounded-b-xl' : 'border-slate-800/80'}`}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400">Status:</span>
              <span
                className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                  isClarification
                    ? 'bg-amber-950 text-amber-300 border border-amber-700 font-bold'
                    : previousEval.quality_band === 'Excellent'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : previousEval.quality_band === 'Good'
                    ? 'bg-blue-950 text-blue-300 border border-blue-800'
                    : previousEval.quality_band === 'Average'
                    ? 'bg-amber-950 text-amber-300 border border-amber-800'
                    : 'bg-rose-950 text-rose-300 border border-rose-800'
                }`}
              >
                {isClarification ? '2nd Go: Details Needed' : previousEval.quality_band}
              </span>
            </div>
            {isClarification ? (
              <span className="text-amber-400 font-medium text-[11px]">
                Score Pending (No 0/10)
              </span>
            ) : (
              <span className="text-slate-400 font-mono">
                +{previousEval.earned_points} / {previousEval.possible_points} pts
              </span>
            )}
          </div>
          <p className="text-slate-300 italic text-[11px] line-clamp-2 mt-1">
            "{previousEval.feedback}"
          </p>
        </div>
      )}
    </div>
  );
};
