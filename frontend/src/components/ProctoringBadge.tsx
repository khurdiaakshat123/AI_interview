import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, X, Clock } from 'lucide-react';
import { ProctoringIncident } from '../types';
import { ProctoringAlert } from '../hooks/useProctoring';

interface ProctoringBadgeProps {
  integrityScore: number;
  integrityStatus: 'HIGH_INTEGRITY' | 'MODERATE_CONCERN' | 'FLAGGED_FOR_REVIEW';
  incidents: ProctoringIncident[];
}

export const ProctoringBadge: React.FC<ProctoringBadgeProps> = ({
  integrityScore,
  integrityStatus,
  incidents
}) => {
  const [showModal, setShowModal] = useState(false);

  const isClean = incidents.length === 0;
  const isHighConcern = integrityStatus === 'FLAGGED_FOR_REVIEW';

  return (
    <>
      <button
        type="button"
        onClick={() => setShowModal(true)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
          isClean
            ? 'bg-emerald-950/50 border-emerald-800/80 text-emerald-300 hover:bg-emerald-900/40'
            : isHighConcern
            ? 'bg-rose-950/60 border-rose-800 text-rose-200 hover:bg-rose-900/50 animate-pulse'
            : 'bg-amber-950/50 border-amber-800/80 text-amber-200 hover:bg-amber-900/40'
        }`}
        title="Click to inspect assessment proctoring and integrity telemetry"
      >
        {isClean ? (
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
        )}
        <span className="hidden sm:inline">Proctoring:</span>
        <span className="font-mono font-bold">{integrityScore}%</span>
        {!isClean && (
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-900/80 text-slate-300 font-mono">
            {incidents.length}
          </span>
        )}
      </button>

      {/* Proctoring Telemetry Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                {isClean ? (
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                ) : (
                  <ShieldAlert className="w-5 h-5 text-amber-400" />
                )}
                <div>
                  <h3 className="text-sm font-bold text-white">Assessment Integrity Telemetry</h3>
                  <p className="text-[11px] text-slate-400">Autonomous browser anti-cheat monitoring</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Score pill */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
              <span className="text-slate-400">Integrity Rating:</span>
              <span className={`font-mono font-bold text-sm ${
                integrityScore >= 85 ? 'text-emerald-400' : integrityScore >= 65 ? 'text-amber-400' : 'text-rose-400'
              }`}>
                {integrityScore} / 100 ({integrityStatus.replace(/_/g, ' ')})
              </span>
            </div>

            {/* Incidents List */}
            <div className="space-y-2">
              <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                Recorded Events ({incidents.length})
              </div>

              {incidents.length === 0 ? (
                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-xs text-emerald-300 text-center">
                  ✓ Zero infractions detected. Session is in continuous high-integrity compliance.
                </div>
              ) : (
                <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1 text-xs">
                  {incidents.map((inc, i) => (
                    <div key={i} className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-200 text-[11px]">{inc.detail}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{inc.timestamp}</div>
                      </div>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-800 text-slate-300 shrink-0">
                        {inc.type.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                Close Telemetry
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export const ProctoringToast: React.FC<{
  alert: ProctoringAlert | null;
  onClose: () => void;
}> = ({ alert, onClose }) => {
  if (!alert) return null;

  const isDanger = alert.type === 'danger';

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full animate-bounce-short shadow-2xl">
      <div className={`p-4 rounded-2xl border backdrop-blur-md flex items-start gap-3 text-xs ${
        isDanger
          ? 'bg-rose-950/95 border-rose-700 text-rose-100'
          : 'bg-amber-950/95 border-amber-700 text-amber-100'
      }`}>
        <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${isDanger ? 'text-rose-400' : 'text-amber-400'}`} />
        <div className="flex-1 space-y-1">
          <div className="font-bold flex items-center justify-between">
            <span>{alert.title}</span>
            <span className="text-[10px] opacity-70 font-mono">{alert.timestamp}</span>
          </div>
          <p className="text-[11px] opacity-90 leading-relaxed">{alert.message}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-white/10 opacity-70 hover:opacity-100 transition-opacity"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
