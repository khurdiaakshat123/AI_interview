import React, { useState, useEffect } from 'react';
import { 
  X, MessageSquare, Clock, Building2, Briefcase, Award, 
  ChevronRight, Calendar, User, Cpu, ArrowUpRight, Loader2, Sparkles
} from 'lucide-react';
import { api } from '../services/api';

interface PastInterviewsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (tab: string, state?: any) => void;
}

export const PastInterviewsModal: React.FC<PastInterviewsModalProps> = ({
  isOpen,
  onClose,
  onNavigate
}) => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<any | null>(null);
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

  // Load list of past interviews when modal opens
  useEffect(() => {
    if (!isOpen) return;
    async function fetchSessions() {
      setLoadingList(true);
      setError(null);
      try {
        const list = await api.getPastInterviews();
        setSessions(list);
        if (list && list.length > 0) {
          setSelectedSessionId(list[0].id);
        } else {
          setSelectedSessionId(null);
          setSessionDetail(null);
        }
      } catch (err: any) {
        console.error('Failed to load past interviews:', err);
        setError('Could not load past interview sessions.');
      } finally {
        setLoadingList(false);
      }
    }
    fetchSessions();
  }, [isOpen]);

  // Fetch full transcript when selectedSessionId changes
  useEffect(() => {
    if (!selectedSessionId) return;
    async function fetchTranscript() {
      setLoadingDetail(true);
      try {
        const data = await api.getInterviewTranscript(selectedSessionId);
        setSessionDetail(data);
      } catch (err) {
        console.error('Failed to load transcript:', err);
      } finally {
        setLoadingDetail(false);
      }
    }
    fetchTranscript();
  }, [selectedSessionId]);

  if (!isOpen) return null;

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

  const formatTime = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div 
        className="w-full max-w-5xl h-[90vh] max-h-[820px] bg-surface border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-bg border border-border flex items-center justify-center text-accent">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-serif font-normal text-text">
                Past Interview Transcripts
              </h2>
              <p className="text-xs text-text-muted font-sans">
                Full conversation dialogues, adaptive follow-ups, and recorded candidate responses
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
          {/* Left Column: Interview Sessions List */}
          <div className="w-full md:w-80 border-b md:border-b-0 md:border-r border-border bg-bg/50 flex flex-col shrink-0 overflow-y-auto">
            <div className="p-3 border-b border-border/60 text-[11px] font-mono uppercase tracking-wider text-text-muted flex items-center justify-between">
              <span>Recorded Sessions</span>
              <span>{sessions.length} total</span>
            </div>

            {loadingList ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-text-muted space-y-2">
                <Loader2 className="w-5 h-5 animate-spin text-accent" />
                <span className="text-xs font-sans">Loading interviews...</span>
              </div>
            ) : error ? (
              <div className="p-4 text-xs text-danger text-center font-sans">{error}</div>
            ) : sessions.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-text-muted space-y-2">
                <MessageSquare className="w-8 h-8 opacity-40 text-text-muted mb-1" />
                <p className="text-xs font-medium text-text">No recorded sessions yet</p>
                <p className="text-[11px] text-text-muted max-w-[200px]">
                  Start an interview session to automatically record full conversation turns here.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {sessions.map((s) => {
                  const isSelected = s.id === selectedSessionId;
                  return (
                    <button
                      key={s.id}
                      onClick={() => setSelectedSessionId(s.id)}
                      className={`w-full text-left p-3.5 transition-colors cursor-pointer flex flex-col gap-1.5 ${
                        isSelected 
                          ? 'bg-surface border-l-2 border-accent text-text' 
                          : 'hover:bg-surface/60 text-text-muted hover:text-text'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-text truncate max-w-[170px]">
                          {s.company}
                        </span>
                        <span className="text-[10px] font-mono text-text-muted">
                          {formatDate(s.created_at)}
                        </span>
                      </div>

                      <div className="text-[11px] text-text-muted truncate">
                        {s.role}
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono pt-1">
                        <span className="text-text-muted">
                          {s.turn_count} {s.turn_count === 1 ? 'turn' : 'turns'}
                        </span>

                        {s.score != null ? (
                          <span className="text-accent font-semibold">
                            Score: {s.score}/100
                          </span>
                        ) : (
                          <span className="text-text-muted/70 text-[10px] uppercase">
                            {s.status === 'COMPLETED' ? 'Completed' : 'Recorded'}
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column: Full Conversation Transcript */}
          <div className="flex-1 flex flex-col min-w-0 bg-surface overflow-hidden">
            {loadingDetail ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-text-muted space-y-2">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
                <span className="text-xs font-sans">Loading full conversation transcript...</span>
              </div>
            ) : !sessionDetail ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-text-muted">
                <p className="text-sm">Select an interview session on the left to read the full conversation.</p>
              </div>
            ) : (
              <>
                {/* Session Details Top Bar */}
                <div className="px-6 py-4 border-b border-border bg-bg/40 flex flex-wrap items-center justify-between gap-3 shrink-0">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-serif font-normal text-text">
                        {sessionDetail.company}
                      </h3>
                      <span className="text-border">·</span>
                      <span className="text-xs text-text-muted font-sans">
                        {sessionDetail.role}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-mono text-text-muted mt-0.5">
                      <span>Candidate: {sessionDetail.candidate_name || 'Candidate'}</span>
                      <span>·</span>
                      <span>{formatDate(sessionDetail.created_at)}</span>
                      <span>·</span>
                      <span>{sessionDetail.transcript?.length || 0} conversation turns</span>
                    </div>
                  </div>

                  {sessionDetail.final_report && onNavigate && (
                    <button
                      onClick={() => {
                        onClose();
                        onNavigate('interview-report', { report: sessionDetail.final_report });
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-accent-contrast text-xs font-medium hover:opacity-90 transition-opacity cursor-pointer"
                    >
                      <Award className="w-3.5 h-3.5" />
                      <span>View Full Scorecard</span>
                    </button>
                  )}
                </div>

                {/* Conversation Turns List */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {(!sessionDetail.transcript || sessionDetail.transcript.length === 0) ? (
                    <div className="text-center py-16 text-text-muted text-xs font-sans">
                      No dialogue recorded in this interview transcript yet.
                    </div>
                  ) : (
                    sessionDetail.transcript.map((turn: any, idx: number) => {
                      const isInterviewer = turn.sender === 'INTERVIEWER';
                      return (
                        <div 
                          key={turn.turn_index || idx}
                          className={`flex flex-col gap-1.5 max-w-3xl ${
                            isInterviewer ? 'mr-auto' : 'ml-auto'
                          }`}
                        >
                          {/* Turn Header */}
                          <div className={`flex items-center gap-2 text-xs font-sans ${
                            isInterviewer ? 'justify-start' : 'justify-end'
                          }`}>
                            {isInterviewer ? (
                              <>
                                <span className="font-semibold text-accent text-[12px]">
                                  AI Technical Interviewer
                                </span>
                                {turn.topic && (
                                  <span className="text-[10px] font-mono text-text-muted bg-surface px-1.5 py-0.5 rounded border border-border">
                                    {turn.topic}
                                  </span>
                                )}
                                {turn.depth_level != null && (
                                  <span className="text-[10px] font-mono text-text-muted">
                                    Depth {turn.depth_level}
                                  </span>
                                )}
                              </>
                            ) : (
                              <>
                                <span className="text-[10px] font-mono text-text-muted">
                                  {formatTime(turn.timestamp)}
                                </span>
                                <span className="font-medium text-text text-[12px]">
                                  {sessionDetail.candidate_name || 'You'}
                                </span>
                              </>
                            )}
                          </div>

                          {/* Message Bubble with Proper Text */}
                          <div className={`p-4 rounded-xl border text-[14px] leading-[1.65] font-sans ${
                            isInterviewer 
                              ? 'bg-surface border-border text-text shadow-sm' 
                              : 'bg-bg border-border text-text'
                          }`}>
                            <p className="whitespace-pre-wrap">{turn.text}</p>
                          </div>
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
