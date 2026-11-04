import React, { useState, useEffect, useRef } from 'react';
import { 
  X, Play, Clock, CheckCircle2, XCircle, Sparkles, 
  ChevronRight, ChevronLeft, RotateCcw, Lightbulb, 
  HelpCircle, Award, BookOpen, Layers, AlertCircle, 
  Check, Filter, ArrowRight 
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { MCQBroadTopic, MCQQuestionSummary, MCQQuizSubmitResult } from '../../types';
import { api } from '../../services/api';
import { MCQCodeBlock } from './MCQCodeBlock';

interface MCQQuizModalProps {
  broadTopics: MCQBroadTopic[];
  initialTopicId?: string;
  onClose: () => void;
  onQuizCompleted?: () => void;
}

export const MCQQuizModal: React.FC<MCQQuizModalProps> = ({
  broadTopics,
  initialTopicId,
  onClose,
  onQuizCompleted
}) => {
  // Step: 'config' | 'running' | 'summary'
  const [step, setStep] = useState<'config' | 'running' | 'summary'>('config');

  // Config State
  const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>(
    initialTopicId ? [initialTopicId] : ['os', 'dbms', 'dsa']
  );
  const [difficulty, setDifficulty] = useState<string>('all');
  const [questionCount, setQuestionCount] = useState<number>(10);
  const [timeLimitMinutes, setTimeLimitMinutes] = useState<number | null>(10); // null = untimed
  const [loading, setLoading] = useState(false);

  // Running Quiz State
  const [quizQuestions, setQuizQuestions] = useState<MCQQuestionSummary[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timeRemaining, setTimeRemaining] = useState<number>(600);
  const [timeSpent, setTimeSpent] = useState<number>(0);
  const [submittingQuiz, setSubmittingQuiz] = useState<boolean>(false);
  const [confirmSubmitModal, setConfirmSubmitModal] = useState<boolean>(false);

  // Summary & Full Review State
  const [quizResult, setQuizResult] = useState<MCQQuizSubmitResult | null>(null);
  const [reviewFilter, setReviewFilter] = useState<'all' | 'incorrect' | 'correct' | 'skipped'>('all');

  // Timer Ref
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Countdown Timer Hook during quiz
  useEffect(() => {
    if (step !== 'running') {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setTimeSpent(prev => prev + 1);

      if (timeLimitMinutes !== null) {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            if (timerRef.current) clearInterval(timerRef.current);
            // Auto submit when time runs out
            handleFinalSubmit(true);
            return 0;
          }
          return prev - 1;
        });
      }
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [step, timeLimitMinutes]);

  const toggleTopic = (id: string) => {
    if (selectedTopicIds.includes(id)) {
      if (selectedTopicIds.length > 1) {
        setSelectedTopicIds(selectedTopicIds.filter(t => t !== id));
      }
    } else {
      setSelectedTopicIds([...selectedTopicIds, id]);
    }
  };

  const handleStartQuiz = async () => {
    setLoading(true);
    try {
      const res = await api.generateMCQQuiz({
        topics: selectedTopicIds,
        difficulties: difficulty !== 'all' ? [difficulty] : undefined,
        count: questionCount,
        mode: 'random'
      });
      setQuizQuestions(res.questions);
      setCurrentIndex(0);
      setAnswers({});
      setQuizResult(null);
      setTimeSpent(0);
      if (timeLimitMinutes !== null) {
        setTimeRemaining(timeLimitMinutes * 60);
      }
      setStep('running');
    } catch (err) {
      console.error('Failed to generate quiz:', err);
    } finally {
      setLoading(false);
    }
  };

  const currentQ = quizQuestions[currentIndex];
  const userOption = currentQ ? answers[currentQ.id] : null;

  const handleSelectOption = (optKey: string) => {
    if (!currentQ || step !== 'running') return;
    // Allow toggle or change choice freely
    setAnswers(prev => ({
      ...prev,
      [currentQ.id]: optKey
    }));
  };

  const handleClearOption = () => {
    if (!currentQ || step !== 'running') return;
    setAnswers(prev => {
      const updated = { ...prev };
      delete updated[currentQ.id];
      return updated;
    });
  };

  const handleNext = () => {
    if (currentIndex < quizQuestions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleFinalSubmit = async (forced: boolean = false) => {
    if (submittingQuiz) return;
    setSubmittingQuiz(true);
    setConfirmSubmitModal(false);

    try {
      const qIds = quizQuestions.map(q => q.id);
      const res = await api.submitMCQQuiz({
        answers,
        question_ids: qIds,
        time_spent_seconds: timeSpent
      });

      setQuizResult(res);
      setStep('summary');

      if (res.score_pct >= 70) {
        confetti({
          particleCount: 60,
          spread: 70,
          origin: { y: 0.6 }
        });
      }

      if (onQuizCompleted) {
        onQuizCompleted();
      }
    } catch (err) {
      console.error('Quiz submission failed:', err);
    } finally {
      setSubmittingQuiz(false);
    }
  };

  // Format MM:SS
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const answeredCount = Object.keys(answers).length;
  const unansweredCount = quizQuestions.length - answeredCount;

  // Filtered review list for summary
  const filteredReviewList = (quizResult?.detailed_results || []).filter(item => {
    if (reviewFilter === 'all') return true;
    if (reviewFilter === 'incorrect') return item.status === 'incorrect';
    if (reviewFilter === 'correct') return item.status === 'correct';
    if (reviewFilter === 'skipped') return item.status === 'skipped';
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-bg/85 backdrop-blur-xs overflow-y-auto">
      <div 
        className="relative w-full max-w-3xl bg-surface border border-border rounded-xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent" />
            <span className="font-medium text-sm text-text">
              {step === 'config' && 'Create Practice Quiz'}
              {step === 'running' && `Quiz Mode • Question ${currentIndex + 1} of ${quizQuestions.length}`}
              {step === 'summary' && 'Quiz Results & Full Review'}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Countdown Timer (Running step) */}
            {step === 'running' && (
              <div className={`flex items-center gap-1.5 px-3 py-1 rounded-lg border font-mono text-xs font-semibold ${
                timeLimitMinutes !== null && timeRemaining <= 60
                  ? 'bg-rose-500/15 border-rose-500/50 text-rose-500 animate-pulse'
                  : 'bg-surface-hover border-border text-text'
              }`}>
                <Clock className="w-3.5 h-3.5 text-accent" />
                <span>
                  {timeLimitMinutes !== null ? formatTime(timeRemaining) : `Elapsed: ${formatTime(timeSpent)}`}
                </span>
              </div>
            )}

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

        {/* STEP 1: CONFIGURATION */}
        {step === 'config' && (
          <div className="p-5 sm:p-6 space-y-5 overflow-y-auto">
            {/* Topic Selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-mono uppercase tracking-wider text-text-muted block">
                  1. Select Broad Topics ({selectedTopicIds.length} selected):
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedTopicIds(broadTopics.map(t => t.id))}
                    className="text-[11px] font-mono text-accent hover:underline cursor-pointer"
                  >
                    Select All
                  </button>
                  <span className="text-text-muted/40">•</span>
                  <button
                    type="button"
                    onClick={() => setSelectedTopicIds(['os', 'dbms', 'computer-networks', 'oop', 'dsa'])}
                    className="text-[11px] font-mono text-accent hover:underline cursor-pointer"
                  >
                    Core CS & DSA
                  </button>
                  <span className="text-text-muted/40">•</span>
                  <button
                    type="button"
                    onClick={() => setSelectedTopicIds(['aptitude'])}
                    className="text-[11px] font-mono text-accent hover:underline cursor-pointer"
                  >
                    Aptitude
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-52 overflow-y-auto pr-1">
                {broadTopics.map(t => {
                  const active = selectedTopicIds.includes(t.id);
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => toggleTopic(t.id)}
                      className={`p-2.5 rounded-lg border text-left text-xs transition-colors flex items-center justify-between cursor-pointer ${
                        active
                          ? 'border-accent bg-accent/10 font-medium text-text'
                          : 'border-border bg-bg text-text-muted hover:text-text hover:bg-surface-hover'
                      }`}
                    >
                      <span className="truncate">{t.name}</span>
                      <span className="text-[10px] font-mono opacity-60 ml-2">{t.total_questions} Qs</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Time Option, Difficulty, & Question Count */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
              {/* Time Option */}
              <div>
                <label className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-2 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-accent" />
                  <span>2. Time Limit:</span>
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {[
                    { label: '5 Mins', val: 5 },
                    { label: '10 Mins', val: 10 },
                    { label: '15 Mins', val: 15 },
                    { label: '20 Mins', val: 20 },
                    { label: '30 Mins', val: 30 },
                    { label: 'No Limit', val: null }
                  ].map(opt => (
                    <button
                      key={opt.label}
                      type="button"
                      onClick={() => setTimeLimitMinutes(opt.val)}
                      className={`py-1.5 px-2 rounded-lg border text-xs font-mono transition-colors cursor-pointer text-center ${
                        timeLimitMinutes === opt.val
                          ? 'bg-text text-bg border-text font-semibold shadow-2xs'
                          : 'bg-surface border-border text-text-muted hover:text-text hover:bg-surface-hover'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Question Count */}
              <div>
                <label className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-2 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-accent" />
                  <span>3. Questions:</span>
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {[5, 10, 15, 20, 25, 30].map(c => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setQuestionCount(c)}
                      className={`py-1.5 px-2 rounded-lg border text-xs font-mono transition-colors cursor-pointer text-center ${
                        questionCount === c
                          ? 'bg-text text-bg border-text font-semibold shadow-2xs'
                          : 'bg-surface border-border text-text-muted hover:text-text hover:bg-surface-hover'
                      }`}
                    >
                      {c} Qs
                    </button>
                  ))}
                </div>
              </div>

              {/* Difficulty */}
              <div>
                <label className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-2">
                  4. Difficulty:
                </label>
                <div className="flex flex-col gap-1.5">
                  {['all', 'Easy', 'Medium', 'Hard'].map(d => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDifficulty(d)}
                      className={`py-1.5 px-2 rounded-lg border text-xs font-medium transition-colors cursor-pointer text-center capitalize ${
                        difficulty === d
                          ? 'bg-text text-bg border-text font-semibold shadow-2xs'
                          : 'bg-surface border-border text-text-muted hover:text-text hover:bg-surface-hover'
                      }`}
                    >
                      {d === 'all' ? 'All Difficulties' : d}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Start Button */}
            <div className="pt-3 border-t border-border flex items-center justify-between">
              <span className="text-xs text-text-muted">
                {timeLimitMinutes ? `Timed Quiz: ${timeLimitMinutes} minutes for ${questionCount} questions` : `Untimed Quiz: ${questionCount} questions`}
              </span>

              <button
                type="button"
                disabled={loading || selectedTopicIds.length === 0}
                onClick={handleStartQuiz}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-accent text-accent-contrast font-medium text-xs shadow-xs hover:bg-accent-hover transition-colors cursor-pointer disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{loading ? 'Generating Quiz...' : 'Start Quiz'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: RUNNING QUIZ (NO IMMEDIATE ANSWERS / NO EXPLANATION SHOWN) */}
        {step === 'running' && currentQ && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Question Quick Jump Palette */}
            <div className="px-5 py-2.5 bg-bg border-b border-border flex items-center gap-1.5 overflow-x-auto scrollbar-none shrink-0">
              <span className="text-[11px] font-mono text-text-muted mr-1">Questions:</span>
              {quizQuestions.map((q, idx) => {
                const isAnswered = !!answers[q.id];
                const isCurrent = idx === currentIndex;
                return (
                  <button
                    key={q.id}
                    type="button"
                    onClick={() => setCurrentIndex(idx)}
                    className={`w-7 h-7 rounded-md text-xs font-mono font-medium transition-colors cursor-pointer shrink-0 border ${
                      isCurrent
                        ? 'border-accent bg-accent text-accent-contrast font-bold'
                        : isAnswered
                        ? 'border-accent/40 bg-accent/15 text-text'
                        : 'border-border bg-surface text-text-muted hover:text-text'
                    }`}
                    title={`Question ${idx + 1}: ${isAnswered ? 'Answered' : 'Unattempted'}`}
                  >
                    {idx + 1}
                  </button>
                );
              })}
            </div>

            {/* Question Workspace */}
            <div className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
              {/* Question metadata badge */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded font-medium bg-surface-hover border border-border text-text text-[11px]">
                    {currentQ.broad_topic_name}
                  </span>
                  <span className="text-text-muted">•</span>
                  <span className="text-text-muted text-[11px] truncate max-w-[200px]">
                    {currentQ.subpart_name}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-hover border border-border text-text-muted">
                    {currentQ.difficulty}
                  </span>
                </div>
                <span className="font-mono text-text-muted text-[11px]">{currentQ.id}</span>
              </div>

              {/* Question Prompt */}
              <div className="text-base sm:text-lg font-serif text-text leading-relaxed tracking-tight">
                {currentQ.question}
              </div>

              {/* Formatted Code Block (if present) */}
              {currentQ.code_snippet && (
                <MCQCodeBlock code={currentQ.code_snippet} title="Code Snippet / Execution Trace" />
              )}

              {/* Interactive Options A, B, C, D (No green/red, no check button) */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-text-muted">
                  <span>Choose Your Answer:</span>
                  {userOption && (
                    <button
                      type="button"
                      onClick={handleClearOption}
                      className="text-text-muted hover:text-rose-500 cursor-pointer lowercase"
                    >
                      clear selection
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {Object.entries(currentQ.options || {}).map(([optKey, optVal]) => {
                    const isSelected = userOption === optKey;

                    return (
                      <button
                        key={optKey}
                        type="button"
                        onClick={() => handleSelectOption(optKey)}
                        className={`w-full p-3.5 rounded-lg border text-left transition-all duration-150 flex items-start gap-3 cursor-pointer ${
                          isSelected
                            ? 'border-accent bg-accent/10 ring-1 ring-accent font-medium'
                            : 'border-border bg-surface hover:bg-surface-hover hover:border-border/80'
                        }`}
                      >
                        <span className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono font-semibold shrink-0 border ${
                          isSelected
                            ? 'bg-accent text-accent-contrast border-accent'
                            : 'bg-surface-hover border-border text-text-muted'
                        }`}>
                          {optKey}
                        </span>

                        <div className="flex-1 text-[13.5px] leading-relaxed text-text font-sans">
                          {optVal}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Bottom Controls Bar */}
            <div className="p-4 border-t border-border bg-surface flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={currentIndex === 0}
                  onClick={handlePrev}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs text-text hover:bg-surface-hover cursor-pointer disabled:opacity-40"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Prev</span>
                </button>
                <button
                  type="button"
                  disabled={currentIndex === quizQuestions.length - 1}
                  onClick={handleNext}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs text-text hover:bg-surface-hover cursor-pointer disabled:opacity-40"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Progress Count & Final Submit */}
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-text-muted hidden sm:inline">
                  {answeredCount} of {quizQuestions.length} answered
                </span>

                <button
                  type="button"
                  disabled={submittingQuiz}
                  onClick={() => {
                    if (unansweredCount > 0) {
                      setConfirmSubmitModal(true);
                    } else {
                      handleFinalSubmit(false);
                    }
                  }}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer shadow-xs hover:bg-accent-hover transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>{submittingQuiz ? 'Submitting...' : 'Submit Quiz'}</span>
                </button>
              </div>
            </div>

            {/* Unanswered confirmation alert modal */}
            {confirmSubmitModal && (
              <div className="absolute inset-0 bg-bg/80 backdrop-blur-xs flex items-center justify-center p-4 z-20">
                <div className="max-w-md w-full bg-surface border border-border p-5 rounded-xl shadow-xl space-y-4">
                  <div className="flex items-center gap-2.5 text-amber-500 font-semibold text-sm">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    <span>Unanswered Questions Remaining</span>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    You have answered <strong className="text-text">{answeredCount}</strong> out of <strong className="text-text">{quizQuestions.length}</strong> questions. There are still <strong className="text-amber-500">{unansweredCount}</strong> unanswered questions.
                  </p>
                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setConfirmSubmitModal(false)}
                      className="px-3.5 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text cursor-pointer"
                    >
                      Continue Quiz
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFinalSubmit(false)}
                      className="px-4 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer"
                    >
                      Submit Anyway
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 3: FULL RESULTS & QUESTION-BY-QUESTION REVIEW */}
        {step === 'summary' && quizResult && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Score Overview Header */}
            <div className="p-5 sm:p-6 border-b border-border bg-surface shrink-0 space-y-4">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3.5 text-left">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 border ${
                    quizResult.score_pct >= 70
                      ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-500'
                      : 'bg-amber-500/15 border-amber-500/30 text-amber-500'
                  }`}>
                    <Award className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-lg font-serif font-bold text-text">
                      {quizResult.score_pct >= 85 ? 'Outstanding Performance!' : quizResult.score_pct >= 60 ? 'Well Done!' : 'Practice Makes Perfect!'}
                    </h2>
                    <p className="text-xs text-text-muted mt-0.5">
                      Completed in {formatTime(quizResult.time_spent_seconds || timeSpent)} • Review detailed calculations below
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setStep('config')}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text cursor-pointer transition-colors"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-accent" />
                    <span>Try Another Quiz</span>
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer hover:bg-accent-hover transition-colors"
                  >
                    Done
                  </button>
                </div>
              </div>

              {/* Score Badges Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
                <div className="p-3 rounded-lg border border-border bg-bg text-center">
                  <span className="text-[10px] font-mono text-text-muted uppercase">Score</span>
                  <div className="text-xl font-bold font-serif text-accent mt-0.5">{quizResult.score_pct}%</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-bg text-center">
                  <span className="text-[10px] font-mono text-emerald-500 uppercase">Correct</span>
                  <div className="text-xl font-bold font-serif text-emerald-500 mt-0.5">{quizResult.correct_count}</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-bg text-center">
                  <span className="text-[10px] font-mono text-rose-500 uppercase">Incorrect</span>
                  <div className="text-xl font-bold font-serif text-rose-500 mt-0.5">{quizResult.incorrect_count}</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-bg text-center">
                  <span className="text-[10px] font-mono text-text-muted uppercase">Skipped</span>
                  <div className="text-xl font-bold font-serif text-text-muted mt-0.5">{quizResult.skipped_count}</div>
                </div>
              </div>

              {/* Review Filter Tabs */}
              <div className="flex items-center justify-between pt-1 border-t border-border/60 text-xs">
                <span className="font-mono text-text-muted text-[11px] uppercase tracking-wider">
                  Detailed Question Review:
                </span>
                <div className="flex items-center gap-1 bg-bg p-0.5 rounded-lg border border-border">
                  {[
                    { id: 'all', label: `All (${quizResult.total_questions})` },
                    { id: 'incorrect', label: `Incorrect (${quizResult.incorrect_count})` },
                    { id: 'correct', label: `Correct (${quizResult.correct_count})` },
                    { id: 'skipped', label: `Skipped (${quizResult.skipped_count})` }
                  ].map(tab => (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setReviewFilter(tab.id as any)}
                      className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                        reviewFilter === tab.id
                          ? 'bg-text text-bg shadow-2xs font-semibold'
                          : 'text-text-muted hover:text-text'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Question-by-Question Review List */}
            <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
              {filteredReviewList.length === 0 ? (
                <div className="py-12 text-center text-text-muted text-xs">
                  No questions match this review filter.
                </div>
              ) : (
                filteredReviewList.map((q, idx) => {
                  const isCorrect = q.status === 'correct';
                  const isSkipped = q.status === 'skipped';
                  const isIncorrect = q.status === 'incorrect';

                  return (
                    <div 
                      key={q.id}
                      className="p-4 sm:p-5 rounded-xl border border-border bg-surface space-y-3.5 shadow-xs"
                    >
                      {/* Question Header & Status */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 pb-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-text">#{idx + 1}</span>
                          <span className="font-mono text-[11px] text-text-muted">{q.id}</span>
                          <span className="px-2 py-0.2 rounded text-[10px] font-medium bg-surface-hover border border-border text-text">
                            {q.broad_topic_name}
                          </span>
                          <span className="text-text-muted text-xs">•</span>
                          <span className="text-[11px] text-text-muted truncate max-w-[200px]">
                            {q.subpart_name}
                          </span>
                        </div>

                        <div>
                          {isCorrect && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Correct</span>
                            </span>
                          )}
                          {isIncorrect && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/30">
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Incorrect</span>
                            </span>
                          )}
                          {isSkipped && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                              <HelpCircle className="w-3.5 h-3.5" />
                              <span>Skipped</span>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Question prompt */}
                      <div className="text-sm sm:text-base font-serif text-text leading-relaxed">
                        {q.question}
                      </div>

                      {/* Code block if present */}
                      {q.code_snippet && (
                        <MCQCodeBlock code={q.code_snippet} title="Code Snippet / Execution Trace" />
                      )}

                      {/* Options Review List with Clear Green/Red Indicators */}
                      <div className="space-y-2 pt-1">
                        {Object.entries(q.options || {}).map(([optKey, optVal]) => {
                          const isCorrectChoice = q.correct_answer === optKey;
                          const isUserChoice = q.user_answer === optKey;

                          let optionStyle = 'border-border/60 bg-bg opacity-70';
                          let badgeStyle = 'bg-surface border-border text-text-muted';

                          if (isCorrectChoice) {
                            optionStyle = 'border-emerald-500/80 bg-emerald-500/15 ring-1 ring-emerald-500/40 opacity-100 font-medium';
                            badgeStyle = 'bg-emerald-500 text-white border-emerald-600 font-bold';
                          } else if (isUserChoice && !isCorrect) {
                            optionStyle = 'border-rose-500/80 bg-rose-500/15 ring-1 ring-rose-500/40 opacity-100 font-medium';
                            badgeStyle = 'bg-rose-500 text-white border-rose-600 font-bold';
                          }

                          return (
                            <div
                              key={optKey}
                              className={`p-3 rounded-lg border text-xs sm:text-[13px] flex items-start gap-3 transition-colors ${optionStyle}`}
                            >
                              <span className={`w-5 h-5 rounded flex items-center justify-center font-mono text-xs border shrink-0 ${badgeStyle}`}>
                                {optKey}
                              </span>
                              <div className="flex-1 leading-relaxed text-text font-sans">
                                {optVal}
                              </div>

                              {isCorrectChoice && (
                                <span className="text-[11px] font-mono text-emerald-500 font-semibold shrink-0">
                                  ✓ Correct Answer
                                </span>
                              )}
                              {isUserChoice && !isCorrect && (
                                <span className="text-[11px] font-mono text-rose-500 font-semibold shrink-0">
                                  ✗ Your Choice
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>

                      {/* Detailed Calculation & Explanation Box */}
                      <div className="p-4 rounded-xl border border-border bg-surface-hover/60 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-accent font-semibold">
                          <Lightbulb className="w-4 h-4" />
                          <span>Detailed Explanation & Calculation:</span>
                        </div>
                        <p className="text-xs sm:text-[13px] text-text leading-relaxed whitespace-pre-line font-sans pt-0.5">
                          {q.explanation}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
