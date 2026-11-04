import React, { useState, useEffect } from 'react';
import { 
  X, Star, ChevronLeft, ChevronRight, CheckCircle2, 
  XCircle, Lightbulb, FileText, Shuffle, Sparkles, 
  Layers, Check, Copy, AlertCircle, BookOpen 
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { MCQQuestionDetail, MCQSubmitResult } from '../../types';
import { api } from '../../services/api';
import { MCQCodeBlock } from './MCQCodeBlock';

interface MCQQuestionModalProps {
  questionId: string;
  onClose: () => void;
  onNavigateQuestion?: (direction: 'prev' | 'next') => void;
  onPickRandom?: () => void;
  onStatusUpdated?: (questionId: string, status: 'todo' | 'attempted' | 'solved', isStarred: boolean) => void;
}

export const MCQQuestionModal: React.FC<MCQQuestionModalProps> = ({
  questionId,
  onClose,
  onNavigateQuestion,
  onPickRandom,
  onStatusUpdated
}) => {
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState<MCQQuestionDetail | null>(null);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<MCQSubmitResult | null>(null);
  const [isStarred, setIsStarred] = useState(false);
  const [notes, setNotes] = useState('');
  const [savingNotes, setSavingNotes] = useState(false);
  const [showNotes, setShowNotes] = useState(false);

  // Load question details
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setLoading(true);
      setSubmitResult(null);
      setSelectedOption(null);
      try {
        const data = await api.getMCQQuestion(questionId);
        if (isMounted) {
          setQuestion(data);
          setIsStarred(data.is_starred || false);
          setNotes(data.notes || '');
          if (data.user_answer) {
            setSelectedOption(data.user_answer);
            // If already answered, show result
            setSubmitResult({
              question_id: data.id,
              selected_option: data.user_answer,
              is_correct: data.is_correct || false,
              correct_answer: data.correct_answer,
              explanation: data.explanation,
              status: data.status,
              attempts_count: data.attempts_count || 1
            });
          }
        }
      } catch (err) {
        console.error('Failed to load MCQ question:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadData();
    return () => { isMounted = false; };
  }, [questionId]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft' && onNavigateQuestion) onNavigateQuestion('prev');
      if (e.key === 'ArrowRight' && onNavigateQuestion) onNavigateQuestion('next');
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onNavigateQuestion]);

  const handleOptionClick = (optKey: string) => {
    if (submitResult) return; // Locked once answered
    setSelectedOption(optKey);
  };

  const handleSubmitAnswer = async () => {
    if (!selectedOption || !question || submitting) return;
    setSubmitting(true);
    try {
      const res = await api.submitMCQAnswer(question.id, selectedOption);
      setSubmitResult(res);
      if (res.is_correct) {
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.7 }
        });
      }
      if (onStatusUpdated) {
        onStatusUpdated(question.id, res.status as any, isStarred);
      }
    } catch (err) {
      console.error('Submit answer failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStar = async () => {
    if (!question) return;
    try {
      const res = await api.toggleMCQStar(question.id);
      setIsStarred(res.is_starred);
      if (onStatusUpdated) {
        const curStatus = submitResult?.status || question.status || 'todo';
        onStatusUpdated(question.id, curStatus as any, res.is_starred);
      }
    } catch (err) {
      console.error('Toggle star failed:', err);
    }
  };

  const handleSaveNotes = async () => {
    if (!question) return;
    setSavingNotes(true);
    try {
      await api.saveMCQNotes(question.id, notes);
    } catch (err) {
      console.error('Save notes failed:', err);
    } finally {
      setSavingNotes(false);
    }
  };

  const getDifficultyColor = (diff: string) => {
    switch (diff?.toLowerCase()) {
      case 'easy':
        return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
      case 'medium':
        return 'text-amber-500 bg-amber-500/10 border-amber-500/20';
      case 'hard':
        return 'text-rose-500 bg-rose-500/10 border-rose-500/20';
      default:
        return 'text-text-muted bg-surface border-border';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-bg/80 backdrop-blur-xs overflow-y-auto">
      <div 
        className="relative w-full max-w-3xl bg-surface border border-border rounded-xl shadow-xl flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-2 text-xs text-text-muted truncate">
            <span className="font-mono text-accent uppercase font-medium">MCQ Question</span>
            <span>•</span>
            <span className="font-medium text-text">{question?.broad_topic_name || 'Broad Topic'}</span>
            <span>•</span>
            <span className="font-mono text-[11px] text-text-muted">{questionId}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleToggleStar}
              className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                isStarred 
                  ? 'border-amber-500/40 text-amber-500 bg-amber-500/10' 
                  : 'border-border text-text-muted hover:text-text hover:bg-surface-hover'
              }`}
              title={isStarred ? "Remove bookmark" : "Bookmark question"}
            >
              <Star className={`w-4 h-4 ${isStarred ? 'fill-amber-500' : ''}`} />
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
              title="Close (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-4">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center text-text-muted space-y-2">
              <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <p className="text-xs">Loading question details...</p>
            </div>
          ) : question ? (
            <>
              {/* Question Metadata Row */}
              <div className="flex flex-wrap items-center justify-between gap-2 pb-1">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${getDifficultyColor(question.difficulty)}`}>
                    {question.difficulty}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-hover border border-border text-text">
                    {question.broad_topic_name}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-text-muted font-mono">
                  <Layers className="w-3.5 h-3.5 text-accent" />
                  <span>Subpart: {question.subpart_name}</span>
                </div>
              </div>

              {/* Question Prompt */}
              <div className="text-base sm:text-lg font-serif text-text leading-relaxed tracking-tight">
                {question.question}
              </div>

              {/* Code Snippet / Operation Trace Box (if present) */}
              {question.code_snippet && (
                <MCQCodeBlock code={question.code_snippet} title="Code Snippet / Execution Trace" />
              )}

              {/* Options Section */}
              <div className="space-y-2.5 pt-2">
                <div className="text-xs font-mono uppercase tracking-wider text-text-muted">
                  Select Answer:
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {Object.entries(question.options || {}).map(([optKey, optVal]) => {
                    const isSelected = selectedOption === optKey;
                    const isSubmitted = !!submitResult;
                    const isCorrectAnswer = submitResult?.correct_answer === optKey;
                    const isUserWrongAnswer = isSubmitted && isSelected && !submitResult.is_correct;

                    let cardClasses = 'border-border bg-surface hover:bg-surface-hover hover:border-border/80';
                    let badgeClasses = 'bg-surface-hover border-border text-text-muted';

                    if (isSubmitted) {
                      if (isCorrectAnswer) {
                        cardClasses = 'border-emerald-500/60 bg-emerald-500/10 ring-1 ring-emerald-500/40';
                        badgeClasses = 'bg-emerald-500 text-white border-emerald-600';
                      } else if (isUserWrongAnswer) {
                        cardClasses = 'border-rose-500/60 bg-rose-500/10 ring-1 ring-rose-500/40';
                        badgeClasses = 'bg-rose-500 text-white border-rose-600';
                      } else {
                        cardClasses = 'opacity-50 border-border bg-surface';
                      }
                    } else if (isSelected) {
                      cardClasses = 'border-accent bg-accent/10 ring-1 ring-accent';
                      badgeClasses = 'bg-accent text-accent-contrast border-accent';
                    }

                    return (
                      <button
                        key={optKey}
                        type="button"
                        disabled={isSubmitted}
                        onClick={() => handleOptionClick(optKey)}
                        className={`w-full p-3.5 rounded-lg border text-left transition-all duration-150 flex items-start gap-3 cursor-pointer disabled:cursor-default ${cardClasses}`}
                      >
                        <span className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono font-semibold shrink-0 border ${badgeClasses}`}>
                          {optKey}
                        </span>

                        <div className="flex-1 text-[13.5px] leading-relaxed text-text font-sans">
                          {optVal}
                        </div>

                        {isSubmitted && isCorrectAnswer && (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                        )}
                        {isSubmitted && isUserWrongAnswer && (
                          <XCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Submit Answer Action */}
              {!submitResult && (
                <div className="pt-3 flex justify-end">
                  <button
                    type="button"
                    disabled={!selectedOption || submitting}
                    onClick={handleSubmitAnswer}
                    className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-accent text-accent-contrast font-medium text-xs shadow-xs hover:bg-accent-hover transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                  >
                    {submitting ? 'Evaluating...' : 'Check Answer'}
                  </button>
                </div>
              )}

              {/* Detailed Explanation Section (Displayed after answering) */}
              {submitResult && (
                <div className="mt-4 p-4 rounded-xl border border-border bg-surface-hover/50 space-y-2 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {submitResult.is_correct ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-500">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Correct Answer! (Option {submitResult.correct_answer})</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-500">
                          <XCircle className="w-4 h-4" />
                          <span>Incorrect. Correct Option is {submitResult.correct_answer}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border">
                    <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-accent mb-1">
                      <Lightbulb className="w-3.5 h-3.5" />
                      <span>Explanation & Calculation</span>
                    </div>
                    <p className="text-xs sm:text-[13px] text-text leading-relaxed whitespace-pre-line font-sans">
                      {submitResult.explanation}
                    </p>
                  </div>
                </div>
              )}

              {/* Candidate Notes Section */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setShowNotes(!showNotes)}
                  className="inline-flex items-center gap-1.5 text-xs font-mono text-text-muted hover:text-text cursor-pointer transition-colors"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>{showNotes ? 'Hide Personal Notes' : (notes ? 'View Notes' : 'Add Personal Note')}</span>
                </button>

                {showNotes && (
                  <div className="mt-2 space-y-2 animate-in fade-in duration-150">
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Write private notes or key takeaways for this question..."
                      rows={3}
                      className="w-full p-2.5 rounded-lg border border-border bg-bg text-text text-xs focus:outline-hidden focus:border-accent resize-none font-sans"
                    />
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={handleSaveNotes}
                        disabled={savingNotes}
                        className="px-3 py-1 rounded bg-surface border border-border text-text hover:bg-surface-hover text-xs font-medium cursor-pointer"
                      >
                        {savingNotes ? 'Saving...' : 'Save Note'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="py-12 text-center text-text-muted text-xs">
              Question not found.
            </div>
          )}
        </div>

        {/* Modal Footer Bar: Navigation & Random */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-border bg-surface shrink-0">
          <div className="flex items-center gap-2">
            {onPickRandom && (
              <button
                type="button"
                onClick={onPickRandom}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text transition-colors cursor-pointer"
                title="Pick random question"
              >
                <Shuffle className="w-3.5 h-3.5 text-accent" />
                <span className="hidden sm:inline">Pick Random</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {onNavigateQuestion && (
              <>
                <button
                  type="button"
                  onClick={() => onNavigateQuestion('prev')}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text transition-colors cursor-pointer"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Prev</span>
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateQuestion('next')}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text transition-colors cursor-pointer"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
