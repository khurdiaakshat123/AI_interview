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
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border transition-colors ${
          isClean
            ? 'bg-surface border-border text-success hover:bg-bg'
            : isHighConcern
            ? 'bg-danger/10 border-danger/30 text-danger hover:bg-danger/20 animate-pulse'
            : 'bg-surface border-border text-accent hover:bg-bg'
        }`}
        title="Click to inspect assessment proctoring and integrity telemetry"
      >
        {isClean ? (
          <ShieldCheck className="w-3.5 h-3.5 text-success" />
        ) : (
          <ShieldAlert className="w-3.5 h-3.5 text-accent" />
        )}
        <span className="hidden sm:inline">Proctoring:</span>
        <span className="font-mono">{integrityScore}%</span>
        {!isClean && (
          <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-bg border border-border text-text-muted font-mono">
            {incidents.length}
          </span>
        )}
      </button>

      {/* Proctoring Telemetry Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 animate-fade-in">
          <div className="bg-surface border border-border rounded-xl max-w-md w-full p-6 space-y-4 relative">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                {isClean ? (
                  <ShieldCheck className="w-5 h-5 text-success" />
                ) : (
                  <ShieldAlert className="w-5 h-5 text-accent" />
                )}
                <div>
                  <h3 className="text-base font-serif text-text font-normal">Assessment Integrity Telemetry</h3>
                  <p className="text-[11px] text-text-muted">Autonomous browser anti-cheat monitoring</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-text-muted hover:text-text rounded-md hover:bg-bg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Score pill */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-bg border border-border text-xs font-mono">
              <span className="text-text-muted">Integrity Rating:</span>
              <span className={`font-medium text-xs ${
                integrityScore >= 85 ? 'text-success' : integrityScore >= 65 ? 'text-accent' : 'text-danger'
              }`}>
                {integrityScore} / 100 ({integrityStatus.replace(/_/g, ' ')})
              </span>
            </div>

            {/* Incidents List */}
            <div className="space-y-2">
              <div className="text-xs font-mono uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-accent" />
                Recorded Events ({incidents.length})
              </div>

              {incidents.length === 0 ? (
                <div className="p-4 rounded-lg bg-success/10 border border-success/30 text-xs text-success text-center font-mono">
                  ✓ Zero infractions detected. Session is in continuous high-integrity compliance.
                </div>
              ) : (
                <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1 text-xs">
                  {incidents.map((inc, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-bg border border-border flex items-start justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="font-medium text-text text-[11px]">{inc.detail}</div>
                        <div className="text-[10px] text-text-muted font-mono">{inc.timestamp}</div>
                      </div>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-medium uppercase bg-surface border border-border text-text-muted shrink-0">
                        {inc.type.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-border flex justify-end">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-1.5 rounded-lg text-xs font-medium bg-bg hover:bg-surface text-text border border-border transition-colors"
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
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full animate-bounce-short">
      <div className={`p-4 rounded-xl border flex items-start gap-3 text-xs ${
        isDanger
          ? 'bg-surface border-danger/40 text-text'
          : 'bg-surface border-border text-text'
      }`}>
        <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${isDanger ? 'text-danger' : 'text-accent'}`} />
        <div className="flex-1 space-y-1">
          <div className="font-semibold flex items-center justify-between text-text">
            <span>{alert.title}</span>
            <span className="text-[10px] text-text-muted font-mono">{alert.timestamp}</span>
          </div>
          <p className="text-[11px] text-text-muted leading-relaxed">{alert.message}</p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded text-text-muted hover:text-text transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
