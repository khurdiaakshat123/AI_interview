import React, { useState, useEffect } from 'react';
import { 
  X, Terminal, Clock, CheckCircle2, XCircle, AlertCircle, 
  ChevronRight, ArrowRight, Loader2, Award, Code2, Play, Layers
} from 'lucide-react';
import { api } from '../services/api';
import { MockOAReport } from '../types';

interface PastOAReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (tab: string, state?: any) => void;
}

export const PastOAReviewModal: React.FC<PastOAReviewModalProps> = ({
  isOpen,
  onClose,
  onNavigate
}) => {
  const [attempts, setAttempts] = useState<any[]>([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<MockOAReport | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Load list of past attempts when modal opens
  useEffect(() => {
    if (!isOpen) return;
    async function fetchAttempts() {
      setLoadingList(true);
      setError(null);
      try {
        const list = await api.getMockOAAttempts();
        setAttempts(list);
        if (list && list.length > 0) {
          setSelectedAttemptId(list[0].id);
        } else {
          setSelectedAttemptId(null);
          setReportDetail(null);
        }
      } catch (err: any) {
        console.error('Failed to load past OA attempts:', err);
        setError('Could not load past assessment records.');
      } finally {
        setLoadingList(false);
      }
    }
    fetchAttempts();
  }, [isOpen]);

  // Fetch full report when selectedAttemptId changes
  useEffect(() => {
    if (!selectedAttemptId) return;
    async function fetchReport() {
      setLoadingDetail(true);
      try {
        const data = await api.getMockOAReport(selectedAttemptId);
        setReportDetail(data);
      } catch (err) {
        console.error('Failed to load assessment report:', err);
      } finally {
        setLoadingDetail(false);
      }
    }
    fetchReport();
  }, [selectedAttemptId]);

  if (!isOpen) return null;

  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs.toString().padStart(2, '0')}s`;
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Recent';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="w-full max-w-5xl h-[90vh] max-h-[840px] bg-surface border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center text-accent">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-serif font-normal text-text">
                Review Past Coding Assessments
              </h2>
              <p className="text-xs text-text-muted font-sans">
                Review time taken, scores, questions solved correctly vs failed, and complete question reviews
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
            title="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
          {/* Left Column: List of Past OA Attempts */}
          <div className="w-full md:w-80 border-b md:border-b-0 md:border-r border-border bg-bg/50 flex flex-col shrink-0 overflow-y-auto">
            <div className="p-3 border-b border-border/60 text-[11px] font-mono uppercase tracking-wider text-text-muted flex items-center justify-between">
              <span>Completed Attempts</span>
              <span>{attempts.length} total</span>
            </div>

            {loadingList ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-text-muted space-y-2">
                <Loader2 className="w-5 h-5 animate-spin text-accent" />
                <span className="text-xs font-sans">Loading assessments...</span>
              </div>
            ) : error ? (
              <div className="p-4 text-xs text-danger text-center font-sans">{error}</div>
            ) : attempts.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-text-muted space-y-2">
                <Terminal className="w-8 h-8 opacity-40 text-text-muted mb-1" />
                <p className="text-xs font-medium text-text">No assessment attempts yet</p>
                <p className="text-[11px] text-text-muted max-w-[200px]">
                  Complete a 60-minute coding assessment to track scores, time, and solved questions here.
                </p>
                {onNavigate && (
                  <button
                    onClick={() => {
                      onClose();
                      onNavigate('mock-oa');
                    }}
                    className="mt-3 px-3 py-1.5 rounded-md bg-accent text-accent-contrast text-xs font-medium hover:opacity-90 transition-opacity cursor-pointer"
                  >
                    Start an Assessment
                  </button>
                )}
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {attempts.map((att) => {
                  const isSelected = att.id === selectedAttemptId;
                  return (
                    <button
                      key={att.id}
                      onClick={() => setSelectedAttemptId(att.id)}
                      className={`w-full text-left p-3.5 transition-colors cursor-pointer flex flex-col gap-1.5 ${
                        isSelected 
                          ? 'bg-surface border-l-2 border-accent text-text' 
                          : 'hover:bg-surface/60 text-text-muted hover:text-text'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-text truncate max-w-[160px]">
                          {att.company}
                        </span>
                        <span className="text-[10px] font-mono text-text-muted">
                          {formatDate(att.submitted_at || att.started_at)}
                        </span>
                      </div>

                      <div className="text-[11px] text-text-muted truncate">
                        {att.role}
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono pt-1">
                        <span className="text-success font-medium">
                          {att.correct_count}/{att.total_questions} Solved
                        </span>

                        <span className="text-accent font-semibold">
                          {att.score}%
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-[10px] font-mono text-text-muted">
                        <Clock className="w-3 h-3 text-text-muted/70" />
                        <span>{formatDuration(att.time_spent_seconds || 0)}</span>
                        <span>·</span>
                        <span>Attempt #{att.attempt_number || 1}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column: Full Assessment Performance Details */}
          <div className="flex-1 flex flex-col min-w-0 bg-surface overflow-hidden">
            {loadingDetail ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-text-muted space-y-2">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
                <span className="text-xs font-sans">Loading assessment review...</span>
              </div>
            ) : !reportDetail ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-text-muted">
                <p className="text-sm">Select an assessment attempt on the left to review question-by-question performance.</p>
              </div>
            ) : (
              <>
                {/* Performance Summary Banner */}
                <div className="px-6 py-4 border-b border-border bg-bg/40 flex flex-wrap items-center justify-between gap-4 shrink-0">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-serif font-normal text-text">
                        {reportDetail.company}
                      </h3>
                      <span className="text-border">·</span>
                      <span className="text-xs text-text-muted font-sans">
                        {reportDetail.role}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-text-muted mt-0.5">
                      Submitted on {formatDate(reportDetail.submitted_at)}
                    </div>
                  </div>

                  {/* Stat Pills */}
                  <div className="flex items-center gap-3">
                    {/* Score */}
                    <div className="px-3 py-1.5 rounded-lg bg-surface border border-border text-center">
                      <span className="block text-[10px] font-mono uppercase text-text-muted">Score</span>
                      <span className="text-sm font-mono font-semibold text-accent">
                        {reportDetail.total_score}%
                      </span>
                    </div>

                    {/* Time */}
                    <div className="px-3 py-1.5 rounded-lg bg-surface border border-border text-center">
                      <span className="block text-[10px] font-mono uppercase text-text-muted">Time Taken</span>
                      <span className="text-sm font-mono font-medium text-text">
                        {formatDuration(reportDetail.time_spent_seconds || 0)}
                      </span>
                    </div>

                    {/* Solved Count */}
                    <div className="px-3 py-1.5 rounded-lg bg-surface border border-border text-center">
                      <span className="block text-[10px] font-mono uppercase text-text-muted">Solved</span>
                      <span className="text-sm font-mono font-medium text-success">
                        {(reportDetail.questions_review || []).filter(q => q.is_correct).length}/{(reportDetail.questions_review || []).length} Correct
                      </span>
                    </div>

                    {onNavigate && (
                      <button
                        onClick={() => {
                          onClose();
                          onNavigate('oa-report', { report: reportDetail });
                        }}
                        className="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-md bg-accent text-accent-contrast text-xs font-medium hover:opacity-90 transition-opacity cursor-pointer"
                      >
                        <Award className="w-3.5 h-3.5" />
                        <span>Full Report View</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Question Reviews List */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {(!reportDetail.questions_review || reportDetail.questions_review.length === 0) ? (
                    <div className="text-center py-16 text-text-muted text-xs font-sans">
                      No question reviews recorded for this attempt.
                    </div>
                  ) : (
                    reportDetail.questions_review.map((q, qIdx) => {
                      return (
                        <div 
                          key={q.question_id || qIdx}
                          className="p-5 rounded-xl border border-border bg-surface shadow-sm space-y-4"
                        >
                          {/* Question Header */}
                          <div className="flex flex-wrap items-start justify-between gap-3 pb-3 border-b border-border/70">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-mono text-xs text-text-muted">Q{qIdx + 1}.</span>
                                <h4 className="text-sm font-semibold text-text">
                                  {q.title || q.topic}
                                </h4>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                                  q.difficulty === 'hard' 
                                    ? 'bg-danger/10 text-danger border border-danger/20'
                                    : q.difficulty === 'medium'
                                      ? 'bg-accent/10 text-accent border border-accent/20'
                                      : 'bg-success/10 text-success border border-success/20'
                                }`}>
                                  {q.difficulty}
                                </span>
                              </div>
                              <div className="text-xs text-text-muted font-sans">
                                {q.subject} · {q.topic}
                              </div>
                            </div>

                            {/* Solved vs Failed Badge */}
                            <div className="flex items-center gap-2">
                              {q.is_correct ? (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-success/15 border border-success/30 text-success text-xs font-medium">
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  Solved Correctly ({q.score}%)
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-danger/15 border border-danger/30 text-danger text-xs font-medium">
                                  <XCircle className="w-3.5 h-3.5" />
                                  Not Solved ({q.score}%)
                                </span>
                              )}
                              <span className="text-[11px] font-mono text-text-muted">
                                {formatDuration(q.time_spent_seconds || 0)}
                              </span>
                            </div>
                          </div>

                          {/* Question Prompt with Proper Text */}
                          <div className="space-y-1.5">
                            <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                              Question Description
                            </span>
                            <div className="p-3.5 rounded-lg bg-bg border border-border/80 text-[13.5px] leading-relaxed text-text font-sans whitespace-pre-wrap">
                              {q.prompt}
                            </div>
                          </div>

                          {/* Candidate Answer / Submitted Code */}
                          {q.user_answer && (
                            <div className="space-y-1.5">
                              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                                Your Submitted Solution
                              </span>
                              <pre className="p-3.5 rounded-lg bg-bg border border-border/80 text-xs font-mono text-text overflow-x-auto leading-relaxed">
                                <code>{q.user_answer}</code>
                              </pre>
                            </div>
                          )}

                          {/* Evaluator Feedback */}
                          {q.feedback && (
                            <div className="p-3 rounded-lg bg-bg/80 border border-border/80 text-xs font-sans text-text flex items-start gap-2">
                              <AlertCircle className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                              <div className="flex-1">
                                <span className="font-semibold text-text block mb-0.5">Evaluation Feedback:</span>
                                <span className="text-text-muted">{q.feedback}</span>
                              </div>
                            </div>
                          )}

                          {/* Test Cases Summary */}
                          {q.test_case_results && q.test_case_results.length > 0 && (
                            <div className="space-y-1.5 pt-1">
                              <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">
                                Test Case Results ({q.test_case_results.filter((tc: any) => tc.passed).length}/{q.test_case_results.length} Passed)
                              </span>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {q.test_case_results.map((tc: any, tcIdx: number) => (
                                  <div 
                                    key={tcIdx}
                                    className={`p-2.5 rounded-lg border text-xs font-mono flex items-center justify-between ${
                                      tc.passed 
                                        ? 'bg-success/5 border-success/30 text-text' 
                                        : 'bg-danger/5 border-danger/30 text-text'
                                    }`}
                                  >
                                    <div className="flex items-center gap-2">
                                      {tc.passed ? (
                                        <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                                      ) : (
                                        <XCircle className="w-3.5 h-3.5 text-danger" />
                                      )}
                                      <span>Test Case #{tc.test_case_index || tcIdx + 1}</span>
                                    </div>
                                    <span className="text-[10px] text-text-muted">
                                      {tc.runtime_ms}ms · {tc.memory_mb}MB
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Optimal Complexity & Approach */}
                          {q.approach && (
                            <div className="pt-1 text-xs text-text-muted font-sans border-t border-border/50">
                              <span className="font-medium text-text">Target Approach: </span>
                              <span>{q.approach}</span>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
