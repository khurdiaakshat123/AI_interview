import React, { useState, useEffect } from 'react';
import { 
  Clock, AlertCircle, CheckCircle2, ChevronLeft, ChevronRight,
  Send, Flag, Code2, Layers, AlertTriangle
} from 'lucide-react';
import { MockOAVariant, Question, MockOAReport } from '../types';
import { Timer } from '../components/Timer';
import { CodeEditor } from '../components/CodeEditor';
import { api } from '../services/api';

interface MockOARunnerPageProps {
  initialCompany?: string;
  initialRole?: string;
  onNavigate: (tab: string, state?: any) => void;
}

export const MockOARunnerPage: React.FC<MockOARunnerPageProps> = ({
  initialCompany = 'Google',
  initialRole = 'Software Engineer II (L4)',
  onNavigate
}) => {
  const [variant, setVariant] = useState<MockOAVariant | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [markedForReview, setMarkedForReview] = useState<Record<string, boolean>>({});
  const [timeSpent, setTimeSpent] = useState<Record<string, number>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmSubmit, setShowConfirmSubmit] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function startOA() {
      try {
        const res = await api.startMockOA({ company: initialCompany, role: initialRole });
        setVariant(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    startOA();
  }, [initialCompany, initialRole]);

  // Track time spent per question
  useEffect(() => {
    if (!variant) return;
    const interval = setInterval(() => {
      const qId = variant.questions[currentIndex]?.id;
      if (qId) {
        setTimeSpent(prev => ({ ...prev, [qId]: (prev[qId] || 0) + 1 }));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [variant, currentIndex]);

  if (loading || !variant) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p>Acquiring canonical Mock OA variant for {initialCompany} in active 7-day window...</p>
      </div>
    );
  }

  const currentQ: Question = variant.questions[currentIndex];
  const currentAnswer = answers[currentQ?.id] ?? (currentQ?.starter_code || '');

  const handleAnswerChange = (val: any) => {
    setAnswers({ ...answers, [currentQ.id]: val });
  };

  const toggleMarkForReview = () => {
    setMarkedForReview({
      ...markedForReview,
      [currentQ.id]: !markedForReview[currentQ.id]
    });
  };

  const handleSubmitExam = async () => {
    setIsSubmitting(true);
    try {
      const report = await api.submitMockOA(variant.mock_oa_attempt_id, {
        answers,
        time_spent_per_question: timeSpent
      });
      onNavigate('oa-report', { report });
    } catch (err) {
      console.error(err);
      alert('Failed to submit exam attempt.');
    } finally {
      setIsSubmitting(false);
      setShowConfirmSubmit(false);
    }
  };

  const answeredCount = Object.keys(answers).filter(k => answers[k] !== '').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Exam Banner Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
        <div className="flex items-center gap-4">
          <div className="px-3 py-1 rounded-xl bg-amber-950/80 border border-amber-800/60 text-amber-300 font-mono text-xs font-bold">
            EXAM IN PROGRESS
          </div>
          <div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>{variant.company} • {variant.role}</span>
              <span className="text-xs text-slate-500 font-normal">
                (Variant #{variant.attempt_number} • Window expires in {variant.window_expires_in_days}d)
              </span>
            </div>
            <span className="text-xs text-slate-400">
              Exam mode: Hints and solutions are locked during timed attempt
            </span>
          </div>
        </div>

        {/* Timer & Submit Controls */}
        <div className="flex items-center gap-3">
          <Timer
            initialMinutes={variant.duration_minutes}
            onTimeExpired={handleSubmitExam}
            isRunning={true}
          />

          <button
            onClick={() => setShowConfirmSubmit(true)}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Send className="w-3.5 h-3.5" />
            Submit OA
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="grid lg:grid-cols-4 gap-6">
        {/* Left 3 Cols: Question and Work Area */}
        <div className="lg:col-span-3 space-y-4">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-brand-950 text-brand-300 border border-brand-800">
                  {currentQ.question_type}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-950 text-amber-300 border border-amber-800">
                  {currentQ.difficulty}
                </span>
                <span className="text-xs text-slate-400 ml-2">{currentQ.topic}</span>
              </div>

              <button
                onClick={toggleMarkForReview}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  markedForReview[currentQ.id]
                    ? 'bg-amber-950 text-amber-300 border border-amber-700'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <Flag className="w-3.5 h-3.5" />
                {markedForReview[currentQ.id] ? 'Marked for Review' : 'Mark for Review'}
              </button>
            </div>

            <h2 className="text-xl font-bold text-white tracking-tight">
              Question {currentIndex + 1}: {currentQ.title || currentQ.subtopic}
            </h2>

            <div className="text-xs sm:text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-sans">
              {currentQ.prompt}
            </div>
          </div>

          {/* Editor or Option Selection */}
          <div>
            {currentQ.question_type.toUpperCase() === 'MCQ' && currentQ.options ? (
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Select Answer Choice
                </div>
                {currentQ.options.map((opt, oIdx) => (
                  <label
                    key={oIdx}
                    onClick={() => handleAnswerChange(opt)}
                    className={`block p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      currentAnswer === opt
                        ? 'bg-brand-600/20 border-brand-500 text-brand-200 font-semibold'
                        : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60'
                    }`}
                  >
                    {opt}
                  </label>
                ))}
              </div>
            ) : currentQ.question_type.toUpperCase() === 'MSQ' && currentQ.options ? (
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Select All Applicable Choices (MSQ)
                </div>
                {currentQ.options.map((opt, oIdx) => {
                  const letter = opt.trim().slice(0, 1);
                  const curList: string[] = Array.isArray(currentAnswer) ? currentAnswer : [];
                  const isChecked = curList.includes(letter);

                  return (
                    <label
                      key={oIdx}
                      onClick={() => {
                        const next = isChecked ? curList.filter(x => x !== letter) : [...curList, letter];
                        handleAnswerChange(next);
                      }}
                      className={`block p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        isChecked
                          ? 'bg-brand-600/20 border-brand-500 text-brand-200 font-semibold'
                          : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60'
                      }`}
                    >
                      {opt}
                    </label>
                  );
                })}
              </div>
            ) : (
              <CodeEditor
                value={currentAnswer}
                onChange={handleAnswerChange}
                language={currentQ.question_type.toLowerCase() === 'sql' ? 'sql' : 'python'}
                onReset={() => handleAnswerChange(currentQ.starter_code || '')}
              />
            )}
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => {
                if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
              }}
              disabled={currentIndex === 0}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous Question
            </button>

            <button
              onClick={() => {
                if (currentIndex < variant.questions.length - 1) setCurrentIndex(currentIndex + 1);
              }}
              disabled={currentIndex === variant.questions.length - 1}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              Next Question
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Right 1 Col: Question Matrix Palette */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between text-xs font-bold text-white pb-3 border-b border-slate-800">
              <span>Question Palette</span>
              <span className="font-mono text-brand-400">{answeredCount}/{variant.questions.length} Solved</span>
            </div>

            <div className="grid grid-cols-4 gap-2">
              {variant.questions.map((q, idx) => {
                const isCurrent = idx === currentIndex;
                const isAnswered = answers[q.id] !== undefined && answers[q.id] !== '';
                const isFlagged = markedForReview[q.id];

                return (
                  <button
                    key={q.id}
                    onClick={() => setCurrentIndex(idx)}
                    className={`h-10 rounded-xl text-xs font-mono font-bold flex flex-col items-center justify-center transition-all ${
                      isCurrent
                        ? 'bg-brand-600 text-white ring-2 ring-brand-400'
                        : isFlagged
                        ? 'bg-amber-950 text-amber-300 border border-amber-700'
                        : isAnswered
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-slate-950 border border-slate-800 text-slate-400 hover:bg-slate-800'
                    }`}
                  >
                    <span>{idx + 1}</span>
                    {isFlagged && <div className="w-1 h-1 rounded-full bg-amber-400 mt-0.5" />}
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="pt-3 border-t border-slate-800 space-y-1.5 text-[11px] text-slate-400">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-emerald-950 border border-emerald-800" />
                <span>Answered</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-amber-950 border border-amber-700" />
                <span>Marked for Review</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-slate-950 border border-slate-800" />
                <span>Unanswered</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmSubmit && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl space-y-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <h3 className="text-lg font-bold text-white">Submit Online Assessment?</h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              You have answered <span className="font-bold text-emerald-400">{answeredCount}</span> of <span className="font-bold text-white">{variant.questions.length}</span> questions.
              Once submitted, your attempt will be finalized and evaluated by Agent 5.
            </p>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowConfirmSubmit(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                Continue Exam
              </button>
              <button
                onClick={handleSubmitExam}
                disabled={isSubmitting}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white flex items-center gap-2 transition-all shadow-md"
              >
                {isSubmitting ? 'Evaluating...' : 'Confirm Submission'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
