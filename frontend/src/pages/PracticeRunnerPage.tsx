import React, { useState } from 'react';
import { 
  CheckCircle2, Lightbulb, Compass, FileCode, Play, RotateCcw,
  ChevronLeft, ChevronRight, Check, X, ArrowLeft
} from 'lucide-react';
import { PracticeSession, Question, CheckAnswerResponse } from '../types';
import { CodeEditor } from '../components/CodeEditor';
import { api } from '../services/api';

interface PracticeRunnerPageProps {
  session: PracticeSession;
  onBack: () => void;
}

export const PracticeRunnerPage: React.FC<PracticeRunnerPageProps> = ({ session, onBack }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [evaluations, setEvaluations] = useState<Record<string, CheckAnswerResponse>>({});
  const [hint, setHint] = useState<string | null>(null);
  const [approach, setApproach] = useState<string | null>(null);
  const [solution, setSolution] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const currentQ: Question = session.questions[currentIndex] || session.questions[0];

  // Initialize answer if empty
  const currentAnswer = answers[currentQ?.id] ?? (currentQ?.starter_code || '');

  const handleAnswerChange = (val: any) => {
    setAnswers({ ...answers, [currentQ.id]: val });
  };

  const handleCheckAnswer = async () => {
    setLoadingAction('check');
    try {
      const res = await api.checkAnswer(currentQ.id, currentAnswer);
      setEvaluations({ ...evaluations, [currentQ.id]: res });
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGetHint = async () => {
    if (hint) {
      setHint(null);
      return;
    }
    setLoadingAction('hint');
    try {
      const res = await api.getHint(currentQ.id);
      setHint(res.hint);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGetApproach = async () => {
    if (approach) {
      setApproach(null);
      return;
    }
    setLoadingAction('approach');
    try {
      const res = await api.getApproach(currentQ.id);
      setApproach(res.approach);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGetSolution = async () => {
    if (solution) {
      setSolution(null);
      return;
    }
    setLoadingAction('solution');
    try {
      const res = await api.getSolution(currentQ.id);
      setSolution(res.solution);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAction(null);
    }
  };

  const currentEval = evaluations[currentQ?.id];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Bar with Navigation & Back */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Back to Configuration"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="text-xs text-brand-400 font-semibold uppercase">
              {session.company} • {session.role}
            </div>
            <h1 className="text-lg font-bold text-white">
              Practice Session <span className="text-xs font-mono text-slate-500">[{session.practice_generation_key.slice(0, 10)}]</span>
            </h1>
          </div>
        </div>

        {/* Question Selector Pills */}
        <div className="flex items-center gap-2">
          {session.questions.map((q, idx) => {
            const isAnswered = evaluations[q.id] !== undefined;
            const isCorrect = evaluations[q.id]?.is_correct;
            const isCurrent = idx === currentIndex;

            return (
              <button
                key={q.id}
                onClick={() => {
                  setCurrentIndex(idx);
                  setHint(null);
                  setApproach(null);
                  setSolution(null);
                }}
                className={`w-8 h-8 rounded-lg text-xs font-mono font-bold flex items-center justify-center transition-all ${
                  isCurrent
                    ? 'bg-brand-600 text-white ring-2 ring-brand-400'
                    : isAnswered
                    ? isCorrect
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-rose-950 text-rose-300 border border-rose-800'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:bg-slate-800'
                }`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left Column: Problem Prompt, Hints, Approaches */}
        <div className="space-y-4">
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-brand-950 text-brand-300 border border-brand-800">
                  {currentQ.question_type}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-amber-950 text-amber-300 border border-amber-800">
                  {currentQ.difficulty}
                </span>
              </div>
              <span className="text-xs text-slate-400">{currentQ.topic}</span>
            </div>

            <h2 className="text-xl font-bold text-white tracking-tight">
              {currentQ.title || currentQ.subtopic}
            </h2>

            <div className="text-xs sm:text-sm text-slate-300 leading-relaxed whitespace-pre-wrap font-sans">
              {currentQ.prompt}
            </div>

            {/* Hint, Approach, Solution Drawers */}
            <div className="pt-4 border-t border-slate-800/80 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={handleGetHint}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    hint ? 'bg-amber-950 text-amber-300 border border-amber-700' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                  {hint ? 'Hide Hint' : 'Hint (Approach Guide)'}
                </button>

                <button
                  onClick={handleGetApproach}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    approach ? 'bg-indigo-950 text-indigo-300 border border-indigo-700' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  <Compass className="w-3.5 h-3.5 text-indigo-400" />
                  {approach ? 'Hide Approach' : 'Optimal Approach'}
                </button>

                <button
                  onClick={handleGetSolution}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    solution ? 'bg-purple-950 text-purple-300 border border-purple-700' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5 text-purple-400" />
                  {solution ? 'Hide Solution' : 'Full Solution'}
                </button>
              </div>

              {hint && (
                <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/60 text-xs text-amber-200">
                  <span className="font-bold block mb-1">💡 Hint:</span>
                  {hint}
                </div>
              )}

              {approach && (
                <div className="p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-800/60 text-xs text-indigo-200">
                  <span className="font-bold block mb-1">🧭 Approach Strategy:</span>
                  {approach}
                </div>
              )}

              {solution && (
                <div className="p-3.5 rounded-xl bg-purple-950/40 border border-purple-800/60 text-xs text-purple-200 space-y-2">
                  <span className="font-bold block">✨ Reference Solution:</span>
                  <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] overflow-x-auto text-slate-200">
                    {solution}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Code Editor or Option Selector + Evaluation */}
        <div className="space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
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

            {/* Test Case Execution Output if available */}
            {currentEval && (
              <div
                className={`p-4 rounded-xl border text-xs space-y-2 ${
                  currentEval.is_correct
                    ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200'
                    : 'bg-rose-950/40 border-rose-800/60 text-rose-200'
                }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <div className="flex items-center gap-2">
                    {currentEval.is_correct ? <Check className="w-4 h-4 text-emerald-400" /> : <X className="w-4 h-4 text-rose-400" />}
                    <span>{currentEval.feedback}</span>
                  </div>
                  <span className="font-mono">
                    Score: {Math.round(currentEval.score_fraction * 100)}%
                  </span>
                </div>

                {currentEval.test_case_results && currentEval.test_case_results.length > 0 && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-800/60">
                    <span className="text-[11px] font-semibold text-slate-400 block">Test Case Breakdown:</span>
                    {currentEval.test_case_results.map((tc, tcIdx) => (
                      <div key={tcIdx} className="flex items-center justify-between text-[11px] font-mono px-2 py-1 rounded bg-slate-900/60">
                        <span>Test #{tc.test_case_index} ({tc.input_data})</span>
                        <span className={tc.passed ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                          {tc.passed ? 'PASSED' : 'FAILED'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between gap-4 pt-4 border-t border-slate-800">
            <button
              onClick={() => {
                if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
              }}
              disabled={currentIndex === 0}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            <button
              onClick={handleCheckAnswer}
              disabled={loadingAction === 'check'}
              className="px-6 py-2 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-2 shadow-sm transition-all"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loadingAction === 'check' ? 'Evaluating...' : 'Check Answer'}
            </button>

            <button
              onClick={() => {
                if (currentIndex < session.questions.length - 1) setCurrentIndex(currentIndex + 1);
              }}
              disabled={currentIndex === session.questions.length - 1}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 flex items-center gap-1.5 transition-colors"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
