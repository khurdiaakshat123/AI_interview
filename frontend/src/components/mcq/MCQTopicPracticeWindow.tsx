import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { 
  ArrowLeft, ChevronLeft, ChevronRight, CheckCircle2, XCircle, 
  Star, Sparkles, BookOpen, Layers, Check, Copy, HelpCircle, 
  Shuffle, RotateCcw, LayoutGrid, AlertCircle, X, ShieldCheck, 
  Lightbulb, ArrowRight, Bookmark, CheckSquare
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { MCQQuestionDetail, MCQQuestionSummary, MCQSubmitResult } from '../../types';
import { api } from '../../services/api';
import { MCQCodeBlock } from './MCQCodeBlock';

interface MCQTopicPracticeWindowProps {
  isOpen: boolean;
  topicId: string;
  topicTitle: string;
  totalQuestionsCount?: number;
  onClose: () => void;
  onProgressUpdated?: () => void;
}

export const MCQTopicPracticeWindow: React.FC<MCQTopicPracticeWindowProps> = ({
  isOpen,
  topicId,
  topicTitle,
  totalQuestionsCount,
  onClose,
  onProgressUpdated
}) => {
  // Questions list in this topic
  const [questions, setQuestions] = useState<MCQQuestionSummary[]>([]);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [currentIndex, setCurrentIndex] = useState<number>(0);

  // Active question full detail
  const [currentDetail, setCurrentDetail] = useState<MCQQuestionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const cachedDetailsRef = useRef<Record<string, MCQQuestionDetail>>({});

  // Question interaction state
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitResult, setSubmitResult] = useState<MCQSubmitResult | null>(null);
  const [isStarred, setIsStarred] = useState<boolean>(false);

  // Question Palette drawer state
  const [paletteOpen, setPaletteOpen] = useState<boolean>(true);
  const [paletteFilter, setPaletteFilter] = useState<'all' | 'todo' | 'solved' | 'attempted' | 'starred'>('all');

  // Load questions for topic on mount
  useEffect(() => {
    if (!isOpen || !topicId) return;

    let isMounted = true;
    setLoadingList(true);
    setCurrentIndex(0);
    setCurrentDetail(null);
    setSubmitResult(null);
    setSelectedOption(null);
    cachedDetailsRef.current = {};

    api.getMCQQuestions({ topic: topicId, limit: 500, page: 1 })
      .then(res => {
        if (!isMounted) return;
        setQuestions(res.questions || []);
        setLoadingList(false);
      })
      .catch(err => {
        console.error('Failed to load topic questions:', err);
        if (isMounted) setLoadingList(false);
      });

    return () => { isMounted = false; };
  }, [isOpen, topicId]);

  // Load specific question detail whenever currentIndex changes
  const activeQuestionSummary = questions[currentIndex];

  useEffect(() => {
    if (!activeQuestionSummary) return;

    const qId = activeQuestionSummary.id;

    // Check if already in cache
    if (cachedDetailsRef.current[qId]) {
      const cached = cachedDetailsRef.current[qId];
      setCurrentDetail(cached);
      setIsStarred(cached.is_starred || false);
      setSelectedOption(cached.user_answer || null);

      if (cached.user_answer && cached.correct_answer) {
        setSubmitResult({
          question_id: cached.id,
          selected_option: cached.user_answer,
          is_correct: cached.is_correct || false,
          correct_answer: cached.correct_answer,
          explanation: cached.explanation || 'Refer to fundamental principles.',
          status: cached.status === 'solved' ? 'solved' : 'attempted',
          attempts_count: cached.attempts_count || 1
        });
      } else {
        setSubmitResult(null);
      }
      return;
    }

    let isMounted = true;
    setLoadingDetail(true);
    setSubmitResult(null);
    setSelectedOption(null);

    api.getMCQQuestion(qId)
      .then(detail => {
        if (!isMounted) return;
        setCurrentDetail(detail);
        setIsStarred(detail.is_starred || false);
        setSelectedOption(detail.user_answer || null);

        cachedDetailsRef.current[qId] = detail;

        if (detail.user_answer && detail.correct_answer) {
          setSubmitResult({
            question_id: detail.id,
            selected_option: detail.user_answer,
            is_correct: detail.is_correct || false,
            correct_answer: detail.correct_answer,
            explanation: detail.explanation || 'Refer to core engineering principles.',
            status: detail.status === 'solved' ? 'solved' : 'attempted',
            attempts_count: detail.attempts_count || 1
          });
        }
        setLoadingDetail(false);
      })
      .catch(err => {
        console.error(`Failed to load detail for question ${qId}:`, err);
        if (isMounted) setLoadingDetail(false);
      });

    return () => { isMounted = false; };
  }, [activeQuestionSummary?.id]);

  // Check Answer Handler
  const handleCheckAnswer = async () => {
    if (!currentDetail || !selectedOption || submitting) return;

    setSubmitting(true);
    try {
      const res = await api.submitMCQAnswer(currentDetail.id, selectedOption);
      setSubmitResult(res);

      // Update question summary in local list to reflect solved/attempted status
      setQuestions(prev => prev.map(q => {
        if (q.id === currentDetail.id) {
          return {
            ...q,
            status: res.is_correct ? 'solved' : 'attempted',
            is_correct: res.is_correct,
            user_answer: selectedOption
          };
        }
        return q;
      }));

      // Update cached detail
      const updatedDetail: MCQQuestionDetail = {
        ...currentDetail,
        user_answer: selectedOption,
        is_correct: res.is_correct,
        status: res.is_correct ? 'solved' : 'attempted',
        correct_answer: res.correct_answer,
        explanation: res.explanation
      };
      setCurrentDetail(updatedDetail);
      cachedDetailsRef.current[currentDetail.id] = updatedDetail;

      // Confetti celebration if correct
      if (res.is_correct) {
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.8 },
          colors: ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6']
        });
      }

      if (onProgressUpdated) onProgressUpdated();
    } catch (err) {
      console.error('Failed to submit answer:', err);
    } finally {
      setSubmitting(false);
    }
  };

  // Toggle Star
  const handleToggleStar = async () => {
    if (!currentDetail) return;
    const nextState = !isStarred;
    setIsStarred(nextState);

    try {
      await api.toggleMCQStar(currentDetail.id);
      // Update local questions list
      setQuestions(prev => prev.map(q => q.id === currentDetail.id ? { ...q, is_starred: nextState } : q));
      // Update cache
      if (cachedDetailsRef.current[currentDetail.id]) {
        cachedDetailsRef.current[currentDetail.id] = {
          ...cachedDetailsRef.current[currentDetail.id],
          is_starred: nextState
        };
      }
    } catch (err) {
      console.error('Failed to toggle star:', err);
      setIsStarred(!nextState); // revert on failure
    }
  };

  // Reset / Retry Current Question
  const handleResetResponse = () => {
    setSelectedOption(null);
    setSubmitResult(null);
  };

  // Navigation handlers
  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.key === 'ArrowRight') {
        handleNext();
      } else if (e.key === 'ArrowLeft') {
        handlePrev();
      } else if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentIndex, questions.length]);

  // Palette Filtering
  const filteredPaletteQuestions = useMemo(() => {
    return questions.filter(q => {
      if (paletteFilter === 'all') return true;
      if (paletteFilter === 'solved') return q.status === 'solved' || q.is_correct === true;
      if (paletteFilter === 'attempted') return q.status === 'attempted' && !q.is_correct;
      if (paletteFilter === 'todo') return !q.status || q.status === 'todo';
      if (paletteFilter === 'starred') return q.is_starred;
      return true;
    });
  }, [questions, paletteFilter]);

  // Overall Topic Stats
  const solvedCount = useMemo(() => questions.filter(q => q.status === 'solved' || q.is_correct).length, [questions]);
  const attemptedCount = useMemo(() => questions.filter(q => q.status === 'attempted' && !q.is_correct).length, [questions]);
  const progressPercent = questions.length > 0 ? Math.round((solvedCount / questions.length) * 100) : 0;

  if (!isOpen) return null;

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg text-text w-full h-full">
      
      {/* 1. Subheader Navigation Bar */}
      <header className="h-14 px-4 sm:px-6 bg-surface border-b border-border flex items-center justify-between shrink-0 shadow-xs z-10">
        
        {/* Left: Back Button & Topic Breadcrumb */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border bg-bg hover:bg-surface-hover text-xs font-semibold text-text transition-colors cursor-pointer shadow-xs active:scale-95"
            title="Return to MCQ Bank"
          >
            <ArrowLeft className="w-4 h-4 text-accent" />
            <span>Back to MCQ Bank</span>
          </button>

          <div className="hidden sm:block h-5 w-px bg-border" />

          <div className="hidden sm:flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent" />
            <span className="text-sm font-bold text-text truncate max-w-xs md:max-w-md">
              {topicTitle}
            </span>
            <span className="text-xs text-text-muted font-mono">
              ({questions.length} Questions)
            </span>
          </div>
        </div>

        {/* Center: Untimed Self-Paced Indicator */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-bg border border-border text-xs font-mono text-text-muted">
          <ShieldCheck className="w-3.5 h-3.5 text-accent" />
          <span>Untimed Self-Paced Practice</span>
        </div>

        {/* Right: Progress Stats & Palette Toggle */}
        <div className="flex items-center gap-3">
          {/* Progress Pill */}
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono">
            <span className="text-emerald-500 font-semibold">{solvedCount} Solved</span>
            <span className="text-text-muted">/</span>
            <span className="text-text-muted">{questions.length} Total</span>
            <span className="text-accent font-semibold">({progressPercent}%)</span>
          </div>

          {/* Toggle Palette Drawer Button */}
          <button
            type="button"
            onClick={() => setPaletteOpen(!paletteOpen)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer shadow-xs ${
              paletteOpen 
                ? 'bg-accent/10 border-accent/30 text-accent ring-1 ring-accent/30' 
                : 'bg-bg border-border text-text hover:bg-surface-hover'
            }`}
            title="Toggle Question Palette Grid"
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>Questions</span>
            <span className="px-1.5 py-0.2 rounded bg-surface border border-border font-mono text-[10px]">
              {currentIndex + 1}/{questions.length || 0}
            </span>
          </button>
        </div>
      </header>

      {/* 2. Main Workspace Body (Question Area + Question Palette) */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left: Main Question Practice Runner */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col justify-between">
          <div className="max-w-3xl mx-auto w-full space-y-6">

            {/* Question Header & Badges */}
            <div className="flex items-center justify-between pb-3 border-b border-border/80">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-surface border border-border text-xs font-mono font-bold text-accent">
                  Question {currentIndex + 1} of {questions.length}
                </span>

                {currentDetail?.difficulty && (
                  <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold uppercase ${
                    currentDetail.difficulty === 'Easy' 
                      ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' 
                      : currentDetail.difficulty === 'Medium'
                      ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                  }`}>
                    {currentDetail.difficulty}
                  </span>
                )}

                {currentDetail?.subpart_name && (
                  <span className="px-2 py-0.5 rounded bg-surface border border-border text-[11px] font-mono text-text-muted">
                    {currentDetail.subpart_name}
                  </span>
                )}

                {currentDetail?.broad_topic_name && (
                  <span className="hidden md:inline px-2 py-0.5 rounded bg-surface border border-border text-[11px] font-mono text-text-muted">
                    {currentDetail.broad_topic_name}
                  </span>
                )}
              </div>

              {/* Star / Bookmark Toggle Button */}
              <button
                type="button"
                onClick={handleToggleStar}
                className={`p-2 rounded-xl border transition-colors cursor-pointer ${
                  isStarred 
                    ? 'bg-amber-500/15 border-amber-500/40 text-amber-500' 
                    : 'bg-surface border-border text-text-muted hover:text-text hover:bg-surface-hover'
                }`}
                title={isStarred ? "Remove from Starred List" : "Star this question"}
              >
                <Star className={`w-4 h-4 ${isStarred ? 'fill-current' : ''}`} />
              </button>
            </div>

            {/* Question Content */}
            {loadingDetail || !currentDetail ? (
              <div className="p-8 rounded-2xl bg-surface border border-border animate-pulse space-y-4">
                <div className="h-5 bg-border/40 rounded w-3/4" />
                <div className="h-5 bg-border/40 rounded w-1/2" />
                <div className="h-32 bg-border/20 rounded-xl" />
                <div className="grid grid-cols-1 gap-3 pt-4">
                  <div className="h-12 bg-border/30 rounded-xl" />
                  <div className="h-12 bg-border/30 rounded-xl" />
                  <div className="h-12 bg-border/30 rounded-xl" />
                  <div className="h-12 bg-border/30 rounded-xl" />
                </div>
              </div>
            ) : (
              <div className="space-y-6">

                {/* Question Statement */}
                <div className="text-base sm:text-lg font-medium text-text leading-relaxed font-sans">
                  {currentDetail.question}
                </div>

                {/* Optional Syntax-Highlighted Code Block */}
                {currentDetail.code_snippet && (
                  <div className="rounded-xl overflow-hidden border border-border">
                    <MCQCodeBlock 
                      code={currentDetail.code_snippet} 
                      language="c" 
                    />
                  </div>
                )}

                {/* Options List */}
                <div className="space-y-3 pt-2">
                  <label className="block text-xs font-mono uppercase tracking-wider text-text-muted">
                    Select Your Answer:
                  </label>

                  <div className="grid grid-cols-1 gap-3">
                    {Object.entries(currentDetail.options || {}).map(([key, text]) => {
                      const isSelected = selectedOption === key;
                      const hasSubmitted = submitResult !== null;
                      const isCorrect = submitResult?.correct_answer === key;
                      const isChosenWrong = hasSubmitted && isSelected && !submitResult?.is_correct;

                      let cardStyle = 'bg-surface border-border hover:bg-surface-hover text-text';

                      if (hasSubmitted) {
                        if (isCorrect) {
                          cardStyle = 'bg-emerald-500/10 border-emerald-500 text-text ring-1 ring-emerald-500 font-semibold';
                        } else if (isChosenWrong) {
                          cardStyle = 'bg-rose-500/10 border-rose-500 text-text ring-1 ring-rose-500';
                        } else {
                          cardStyle = 'bg-surface/50 border-border/60 text-text-muted opacity-60';
                        }
                      } else if (isSelected) {
                        cardStyle = 'bg-accent/10 border-accent text-text ring-1 ring-accent font-medium shadow-xs';
                      }

                      return (
                        <div
                          key={key}
                          role="radio"
                          aria-checked={isSelected}
                          tabIndex={!hasSubmitted ? 0 : -1}
                          onClick={() => {
                            if (!hasSubmitted) setSelectedOption(key);
                          }}
                          onKeyDown={(e) => {
                            if (!hasSubmitted && (e.key === ' ' || e.key === 'Enter')) {
                              e.preventDefault();
                              setSelectedOption(key);
                            }
                          }}
                          className={`p-4 rounded-xl border transition-all duration-150 flex items-start gap-3.5 select-none focus:outline-none focus:ring-2 focus:ring-accent ${
                            !hasSubmitted ? 'cursor-pointer active:scale-[0.995]' : 'cursor-default'
                          } ${cardStyle}`}
                        >
                          {/* Option Badge (A, B, C, D) */}
                          <div className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center font-mono font-bold text-xs border ${
                            hasSubmitted && isCorrect
                              ? 'bg-emerald-500 border-emerald-500 text-white'
                              : hasSubmitted && isChosenWrong
                              ? 'bg-rose-500 border-rose-500 text-white'
                              : isSelected
                              ? 'bg-accent border-accent text-accent-contrast'
                              : 'bg-bg border-border text-text-muted'
                          }`}>
                            {hasSubmitted && isCorrect ? (
                              <Check className="w-4 h-4" />
                            ) : hasSubmitted && isChosenWrong ? (
                              <X className="w-4 h-4" />
                            ) : (
                              key
                            )}
                          </div>

                          {/* Option Text */}
                          <div className="flex-1 text-sm font-sans pt-0.5 leading-relaxed break-words">
                            {text}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Explanation Card (Revealed upon Checking) */}
                {submitResult && (
                  <div className={`p-5 rounded-2xl border animate-in fade-in slide-in-from-top-2 duration-200 space-y-3 ${
                    submitResult.is_correct 
                      ? 'bg-emerald-500/5 border-emerald-500/30 ring-1 ring-emerald-500/20' 
                      : 'bg-rose-500/5 border-rose-500/30 ring-1 ring-rose-500/20'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {submitResult.is_correct ? (
                          <div className="flex items-center gap-1.5 text-emerald-500 font-bold text-sm">
                            <CheckCircle2 className="w-5 h-5" />
                            <span>Correct Answer! Well done.</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-rose-500 font-bold text-sm">
                            <XCircle className="w-5 h-5" />
                            <span>Incorrect Response</span>
                          </div>
                        )}
                      </div>

                      <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-md bg-surface border border-border text-text">
                        Correct Option: <strong className="text-emerald-500">{submitResult.correct_answer}</strong>
                      </span>
                    </div>

                    <div className="pt-2 border-t border-border/50 text-xs sm:text-sm text-text/90 leading-relaxed font-sans space-y-2">
                      <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-text uppercase tracking-wider">
                        <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                        <span>Detailed Explanation</span>
                      </div>
                      <p className="whitespace-pre-line text-text-muted">
                        {submitResult.explanation || currentDetail.explanation || 'Refer to standard operating system textbooks and official documentation.'}
                      </p>
                    </div>

                    <div className="flex items-center justify-end pt-1">
                      <button
                        type="button"
                        onClick={handleResetResponse}
                        className="inline-flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text cursor-pointer transition-colors"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Try Again / Clear Selection</span>
                      </button>
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>

          {/* Bottom Action Footer Bar */}
          <div className="max-w-3xl mx-auto w-full pt-8 pb-4 border-t border-border mt-8 flex items-center justify-between gap-3">
            {/* Previous Question Button */}
            <button
              type="button"
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-border bg-surface hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-text transition-all cursor-pointer shadow-xs"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>

            {/* Check Answer OR Next Question CTA */}
            <div>
              {submitResult === null ? (
                <button
                  type="button"
                  onClick={handleCheckAnswer}
                  disabled={!selectedOption || submitting}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-accent text-accent-contrast hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition-all shadow-md cursor-pointer active:scale-95"
                >
                  <CheckSquare className="w-4 h-4" />
                  <span>{submitting ? 'Checking...' : 'Check Answer'}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleNext}
                  disabled={currentIndex >= questions.length - 1}
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs font-bold transition-all shadow-md cursor-pointer active:scale-95"
                >
                  <span>Next Question</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Next Question Button */}
            <button
              type="button"
              onClick={handleNext}
              disabled={currentIndex >= questions.length - 1}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-border bg-surface hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold text-text transition-all cursor-pointer shadow-xs"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </main>

        {/* Right: Question Palette Drawer */}
        {paletteOpen && (
          <aside className="w-80 border-l border-border bg-surface flex flex-col shrink-0 animate-in slide-in-from-right-2 duration-150 shadow-md">
            
            {/* Palette Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-text flex items-center gap-1.5 font-mono">
                  <LayoutGrid className="w-3.5 h-3.5 text-accent" />
                  <span>Question Navigator</span>
                </h3>
                <span className="text-[11px] text-text-muted font-mono">
                  {questions.length} Questions in {topicTitle}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setPaletteOpen(false)}
                className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-surface-hover"
                title="Hide palette"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Filter Chips inside Palette */}
            <div className="p-3 border-b border-border flex items-center gap-1.5 overflow-x-auto text-xs font-mono scrollbar-none">
              {(['all', 'todo', 'solved', 'starred'] as const).map(filterKey => (
                <button
                  key={filterKey}
                  type="button"
                  onClick={() => setPaletteFilter(filterKey)}
                  className={`px-2.5 py-1 rounded-md text-[11px] capitalize font-medium transition-colors cursor-pointer shrink-0 ${
                    paletteFilter === filterKey
                      ? 'bg-accent text-accent-contrast shadow-xs'
                      : 'bg-bg text-text-muted hover:text-text border border-border'
                  }`}
                >
                  {filterKey}
                </button>
              ))}
            </div>

            {/* Quick Status Legend */}
            <div className="px-4 py-2.5 bg-bg/50 border-b border-border flex items-center justify-between text-[11px] font-mono text-text-muted">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
                <span>Solved ({solvedCount})</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                <span>Attempted ({attemptedCount})</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-surface border border-border inline-block" />
                <span>Todo</span>
              </span>
            </div>

            {/* Numbers Grid */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="grid grid-cols-5 gap-2">
                {questions.map((q, idx) => {
                  const isCurrent = idx === currentIndex;
                  const isSolved = q.status === 'solved' || q.is_correct === true;
                  const isAttempted = q.status === 'attempted' && !q.is_correct;
                  const isStarredQ = q.is_starred;

                  let btnStyle = 'bg-bg border-border text-text hover:bg-surface-hover';
                  if (isSolved) {
                    btnStyle = 'bg-emerald-500/15 border-emerald-500/60 text-emerald-600 dark:text-emerald-400 font-semibold';
                  } else if (isAttempted) {
                    btnStyle = 'bg-rose-500/15 border-rose-500/60 text-rose-600 dark:text-rose-400 font-semibold';
                  }

                  if (isCurrent) {
                    btnStyle += ' ring-2 ring-accent border-accent font-bold scale-105 shadow-sm';
                  }

                  return (
                    <button
                      key={q.id}
                      type="button"
                      onClick={() => setCurrentIndex(idx)}
                      className={`relative h-10 rounded-xl border flex flex-col items-center justify-center font-mono text-xs transition-all cursor-pointer ${btnStyle}`}
                      title={`Jump to Question #${idx + 1}`}
                    >
                      <span>{idx + 1}</span>
                      {isStarredQ && (
                        <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-400" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

          </aside>
        )}

      </div>
    </div>
  );
};
