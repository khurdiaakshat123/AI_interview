import React, { useState } from 'react';
import { 
  X, Play, Clock, CheckCircle2, XCircle, Sparkles, 
  ChevronRight, ChevronLeft, RotateCcw, Lightbulb, 
  HelpCircle, Award, BookOpen, Layers 
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { MCQBroadTopic, MCQQuestionSummary } from '../../types';
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
  const [loading, setLoading] = useState(false);

  // Running Quiz State
  const [quizQuestions, setQuizQuestions] = useState<MCQQuestionSummary[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, { is_correct: boolean; correct_answer: string; explanation: string }>>({});
  const [evaluatedCurrent, setEvaluatedCurrent] = useState(false);

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
      setResults({});
      setEvaluatedCurrent(false);
      setStep('running');
    } catch (err) {
      console.error('Failed to generate quiz:', err);
    } finally {
      setLoading(false);
    }
  };

  const currentQ = quizQuestions[currentIndex];
  const userOption = currentQ ? answers[currentQ.id] : null;
  const currentResult = currentQ ? results[currentQ.id] : null;

  const handleSelectOption = (optKey: string) => {
    if (currentResult || !currentQ) return;
    setAnswers({ ...answers, [currentQ.id]: optKey });
  };

  const handleCheckAnswer = async () => {
    if (!currentQ || !userOption) return;
    try {
      const res = await api.submitMCQAnswer(currentQ.id, userOption);
      setResults({
        ...results,
        [currentQ.id]: {
          is_correct: res.is_correct,
          correct_answer: res.correct_answer,
          explanation: res.explanation
        }
      });
      setEvaluatedCurrent(true);
      if (res.is_correct) {
        confetti({ particleCount: 30, spread: 50 });
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleNext = () => {
    if (currentIndex < quizQuestions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setEvaluatedCurrent(!!results[quizQuestions[currentIndex + 1]?.id]);
    } else {
      // Finished all questions
      setStep('summary');
      if (onQuizCompleted) onQuizCompleted();
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setEvaluatedCurrent(!!results[quizQuestions[currentIndex - 1]?.id]);
    }
  };

  // Calculate score summary
  const totalQuestions = quizQuestions.length;
  const answeredCount = Object.keys(results).length;
  const correctCount = Object.values(results).filter(r => r.is_correct).length;
  const scorePct = totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-bg/80 backdrop-blur-xs overflow-y-auto">
      <div 
        className="relative w-full max-w-2xl bg-surface border border-border rounded-xl shadow-xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border bg-surface shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent" />
            <span className="font-medium text-sm text-text">
              {step === 'config' && 'Create Practice Quiz'}
              {step === 'running' && `Quiz Mode • Question ${currentIndex + 1} of ${totalQuestions}`}
              {step === 'summary' && 'Quiz Summary & Report'}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* STEP 1: CONFIGURATION */}
        {step === 'config' && (
          <div className="p-5 sm:p-6 space-y-5 overflow-y-auto">
            <div>
              <label className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-2">
                1. Select Broad Topics ({selectedTopicIds.length} selected):
              </label>
              <div className="flex items-center gap-2 mb-2">
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
                  Aptitude Only
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
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
                          : 'border-border bg-bg text-text-muted hover:text-text'
                      }`}
                    >
                      <span className="truncate">{t.name}</span>
                      <span className="text-[10px] font-mono opacity-60 ml-2">{t.total_questions} Qs</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-2">
                  2. Difficulty:
                </label>
                <div className="flex items-center gap-2">
                  {['all', 'Easy', 'Medium', 'Hard'].map(d => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDifficulty(d)}
                      className={`flex-1 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer capitalize ${
                        difficulty === d
                          ? 'bg-text text-bg border-text'
                          : 'bg-surface border-border text-text-muted hover:text-text'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-mono uppercase tracking-wider text-text-muted block mb-2">
                  3. Question Count:
                </label>
                <div className="flex items-center gap-2">
                  {[5, 10, 15, 20].map(c => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setQuestionCount(c)}
                      className={`flex-1 py-1.5 rounded-lg border text-xs font-mono font-medium transition-colors cursor-pointer ${
                        questionCount === c
                          ? 'bg-text text-bg border-text'
                          : 'bg-surface border-border text-text-muted hover:text-text'
                      }`}
                    >
                      {c} Qs
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                disabled={loading || selectedTopicIds.length === 0}
                onClick={handleStartQuiz}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-accent text-accent-contrast font-medium text-xs shadow-xs hover:bg-accent-hover transition-colors cursor-pointer disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{loading ? 'Creating Quiz...' : 'Start Quiz'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: RUNNING QUIZ */}
        {step === 'running' && currentQ && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
              {/* Question metadata badge */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded font-medium bg-surface-hover border border-border text-text text-[11px]">
                    {currentQ.broad_topic_name}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface-hover border border-border text-text-muted">
                    {currentQ.difficulty}
                  </span>
                </div>
                <span className="font-mono text-text-muted text-[11px]">{currentQ.id}</span>
              </div>

              {/* Question text */}
              <div className="text-base font-serif text-text leading-relaxed">
                {currentQ.question}
              </div>

              {/* Code snippet if present */}
              {currentQ.code_snippet && (
                <MCQCodeBlock code={currentQ.code_snippet} />
              )}

              {/* Options */}
              <div className="space-y-2 pt-2">
                {Object.entries(currentQ.options || {}).map(([optKey, optVal]) => {
                  const isSelected = userOption === optKey;
                  const hasAnswered = !!currentResult;
                  const isCorrect = currentResult?.correct_answer === optKey;
                  const isWrong = hasAnswered && isSelected && !currentResult.is_correct;

                  let cardStyle = 'border-border bg-surface hover:bg-surface-hover';
                  if (hasAnswered) {
                    if (isCorrect) cardStyle = 'border-emerald-500/60 bg-emerald-500/10 ring-1 ring-emerald-500/40';
                    else if (isWrong) cardStyle = 'border-rose-500/60 bg-rose-500/10 ring-1 ring-rose-500/40';
                    else cardStyle = 'opacity-50 border-border bg-surface';
                  } else if (isSelected) {
                    cardStyle = 'border-accent bg-accent/10 ring-1 ring-accent';
                  }

                  return (
                    <button
                      key={optKey}
                      type="button"
                      disabled={hasAnswered}
                      onClick={() => handleSelectOption(optKey)}
                      className={`w-full p-3 rounded-lg border text-left text-xs sm:text-[13px] flex items-start gap-3 transition-colors cursor-pointer ${cardStyle}`}
                    >
                      <span className="w-5 h-5 rounded flex items-center justify-center font-mono font-bold border border-border shrink-0 bg-surface">
                        {optKey}
                      </span>
                      <span className="flex-1 leading-relaxed text-text">{optVal}</span>
                    </button>
                  );
                })}
              </div>

              {/* Explanation on submit */}
              {currentResult && (
                <div className="mt-3 p-3.5 rounded-lg border border-border bg-surface-hover/50 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold text-text">
                    <Lightbulb className="w-3.5 h-3.5 text-accent" />
                    <span>Explanation:</span>
                  </div>
                  <p className="text-text-muted whitespace-pre-line leading-relaxed">{currentResult.explanation}</p>
                </div>
              )}
            </div>

            {/* Bottom Controls */}
            <div className="p-4 border-t border-border bg-surface flex items-center justify-between shrink-0">
              <button
                type="button"
                disabled={currentIndex === 0}
                onClick={handlePrev}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border text-xs text-text-muted hover:text-text cursor-pointer disabled:opacity-40"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              <div>
                {!currentResult ? (
                  <button
                    type="button"
                    disabled={!userOption}
                    onClick={handleCheckAnswer}
                    className="px-4 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer disabled:opacity-40"
                  >
                    Check
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleNext}
                    className="inline-flex items-center gap-1 px-4 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer"
                  >
                    <span>{currentIndex === quizQuestions.length - 1 ? 'Finish Quiz' : 'Next'}</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: SUMMARY REPORT */}
        {step === 'summary' && (
          <div className="p-6 space-y-6 overflow-y-auto text-center">
            <div className="flex flex-col items-center justify-center space-y-2">
              <div className="w-14 h-14 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center text-accent">
                <Award className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-serif text-text font-semibold">Quiz Complete!</h2>
              <p className="text-xs text-text-muted">You scored {correctCount} out of {totalQuestions} questions.</p>
            </div>

            <div className="grid grid-cols-3 gap-3 p-4 rounded-xl border border-border bg-bg text-center">
              <div>
                <span className="text-[11px] font-mono text-text-muted uppercase">Score</span>
                <p className="text-xl font-bold text-accent">{scorePct}%</p>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted uppercase">Correct</span>
                <p className="text-xl font-bold text-emerald-500">{correctCount}</p>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted uppercase">Incorrect</span>
                <p className="text-xl font-bold text-rose-500">{totalQuestions - correctCount}</p>
              </div>
            </div>

            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setStep('config')}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-surface hover:bg-surface-hover text-xs font-medium text-text cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Try Another Quiz</span>
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 rounded-lg bg-accent text-accent-contrast text-xs font-medium cursor-pointer"
              >
                Back to Questions
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
