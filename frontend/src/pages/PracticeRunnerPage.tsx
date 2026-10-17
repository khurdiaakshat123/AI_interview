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
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-surface border border-border text-text-muted hover:text-text transition-colors"
            title="Back to Configuration"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="text-xs font-mono uppercase text-accent font-medium">
              {session.company} • {session.role}
            </div>
            <h1 className="text-lg font-serif text-text font-normal">
              Practice Session <span className="text-xs font-mono text-text-muted">[{session.practice_generation_key.slice(0, 10)}]</span>
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
                className={`w-8 h-8 rounded-lg text-xs font-mono transition-colors flex items-center justify-center ${
                  isCurrent
                    ? 'bg-accent text-accent-contrast font-medium'
                    : isAnswered
                    ? isCorrect
                      ? 'bg-success/15 text-success border border-success/30'
                      : 'bg-danger/15 text-danger border border-danger/30'
                    : 'bg-surface border border-border text-text-muted hover:text-text'
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
          <div className="p-6 rounded-xl bg-surface border border-border space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-bg border border-border text-text-muted">
                  {currentQ.question_type}
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono uppercase bg-bg border border-border text-accent">
                  {currentQ.difficulty}
                </span>
              </div>
              <span className="text-xs text-text-muted font-mono">{currentQ.topic}</span>
            </div>

            <h2 className="text-xl font-serif text-text font-normal tracking-tight">
              {currentQ.title || currentQ.subtopic}
            </h2>

            <div className="text-sm text-text leading-relaxed whitespace-pre-wrap font-sans">
              {currentQ.prompt}
            </div>

            {/* Hint, Approach, Solution Drawers */}
            <div className="pt-4 border-t border-border space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={handleGetHint}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    hint ? 'bg-bg text-accent border-accent' : 'bg-surface hover:bg-border text-text border-border'
                  }`}
                >
                  <Lightbulb className="w-3.5 h-3.5 text-accent" />
                  {hint ? 'Hide Hint' : 'Hint (Approach Guide)'}
                </button>

                <button
                  onClick={handleGetApproach}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    approach ? 'bg-bg text-accent border-accent' : 'bg-surface hover:bg-border text-text border-border'
                  }`}
                >
                  <Compass className="w-3.5 h-3.5 text-accent" />
                  {approach ? 'Hide Approach' : 'Optimal Approach'}
                </button>

                <button
                  onClick={handleGetSolution}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    solution ? 'bg-bg text-accent border-accent' : 'bg-surface hover:bg-border text-text border-border'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5 text-accent" />
                  {solution ? 'Hide Solution' : 'Full Solution'}
                </button>
              </div>

              {hint && (
                <div className="p-3.5 rounded-lg bg-bg border border-border text-xs text-text leading-relaxed">
                  <span className="font-semibold block mb-1 text-accent font-mono">Hint:</span>
                  {hint}
                </div>
              )}

              {approach && (
                <div className="p-3.5 rounded-lg bg-bg border border-border text-xs text-text leading-relaxed">
                  <span className="font-semibold block mb-1 text-accent font-mono">Approach Strategy:</span>
                  {approach}
                </div>
              )}

              {solution && (
                <div className="p-3.5 rounded-lg bg-bg border border-border text-xs text-text space-y-2">
                  <span className="font-semibold block text-accent font-mono">Reference Solution:</span>
                  <pre className="p-3 rounded-lg bg-surface border border-border font-mono text-[11px] overflow-x-auto text-text">
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
              <div className="p-6 rounded-xl bg-surface border border-border space-y-3">
                <div className="text-xs font-mono uppercase tracking-wider text-text-muted mb-2">
                  Select Answer Choice
                </div>
                {currentQ.options.map((opt, oIdx) => (
                  <label
                    key={oIdx}
                    onClick={() => handleAnswerChange(opt)}
                    className={`block p-3.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                      currentAnswer === opt
                        ? 'bg-bg border-accent text-text font-medium'
                        : 'bg-bg/40 border-border text-text-muted hover:text-text hover:bg-bg'
                    }`}
                  >
                    {opt}
                  </label>
                ))}
              </div>
            ) : currentQ.question_type.toUpperCase() === 'MSQ' && currentQ.options ? (
              <div className="p-6 rounded-xl bg-surface border border-border space-y-3">
                <div className="text-xs font-mono uppercase tracking-wider text-text-muted mb-2">
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
                      className={`block p-3.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                        isChecked
                          ? 'bg-bg border-accent text-text font-medium'
                          : 'bg-bg/40 border-border text-text-muted hover:text-text hover:bg-bg'
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
                className={`p-4 rounded-xl border text-xs space-y-2 font-mono ${
                  currentEval.is_correct
                    ? 'bg-success/10 border-success/30 text-success'
                    : 'bg-danger/10 border-danger/30 text-danger'
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <div className="flex items-center gap-2">
                    {currentEval.is_correct ? <Check className="w-4 h-4 text-success" /> : <X className="w-4 h-4 text-danger" />}
                    <span>{currentEval.feedback}</span>
                  </div>
                  <span>
                    Score: {Math.round(currentEval.score_fraction * 100)}%
                  </span>
                </div>

                {currentEval.test_case_results && currentEval.test_case_results.length > 0 && (
                  <div className="space-y-1.5 pt-2 border-t border-border">
                    <span className="text-[11px] font-mono text-text-muted block">Test Case Breakdown:</span>
                    {currentEval.test_case_results.map((tc, tcIdx) => (
                      <div key={tcIdx} className="flex items-center justify-between text-[11px] px-2 py-1 rounded bg-bg border border-border">
                        <span>Test #{tc.test_case_index} ({tc.input_data})</span>
                        <span className={tc.passed ? 'text-success font-semibold' : 'text-danger font-semibold'}>
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
          <div className="flex items-center justify-between gap-4 pt-4 border-t border-border">
            <button
              onClick={() => {
                if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
              }}
              disabled={currentIndex === 0}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-surface hover:bg-border disabled:opacity-40 text-text flex items-center gap-1.5 transition-colors border border-border"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            <button
              onClick={handleCheckAnswer}
              disabled={loadingAction === 'check'}
              className="px-6 py-2 rounded-lg text-xs font-medium bg-accent text-accent-contrast hover:opacity-90 disabled:opacity-40 flex items-center gap-2 transition-opacity"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loadingAction === 'check' ? 'Evaluating...' : 'Check Answer'}
            </button>

            <button
              onClick={() => {
                if (currentIndex < session.questions.length - 1) setCurrentIndex(currentIndex + 1);
              }}
              disabled={currentIndex === session.questions.length - 1}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-surface hover:bg-border disabled:opacity-40 text-text flex items-center gap-1.5 transition-colors border border-border"
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
