import React, { useState, useEffect } from 'react';
import { 
  Clock, AlertCircle, CheckCircle2, ChevronLeft, ChevronRight,
  Send, Flag, Code2, Layers, AlertTriangle, Play, Terminal, 
  Check, X, Sparkles, RefreshCw, Eye
} from 'lucide-react';
import { MockOAVariant, Question, MockOAReport } from '../types';
import { Timer } from '../components/Timer';
import { CodeEditor } from '../components/CodeEditor';
import { useProctoring } from '../hooks/useProctoring';
import { ProctoringBadge, ProctoringToast } from '../components/ProctoringBadge';
import { api } from '../services/api';
import { generateBoilerplate, SUPPORTED_LANGUAGES } from '../utils/boilerplate_generator';

interface MockOARunnerPageProps {
  initialCompany?: string;
  initialRole?: string;
  onNavigate: (tab: string, state?: any) => void;
}

interface TestCaseResultItem {
  test_case_index: number;
  input_data: string;
  expected_output: string;
  actual_output: string;
  passed: boolean;
  runtime_ms: number;
  memory_mb: number;
}

interface RunResult {
  status: 'ACCEPTED' | 'WRONG_ANSWER' | 'COMPILATION_ERROR' | 'RUNTIME_ERROR' | 'TLE';
  runtime_ms: number;
  memory_mb: number;
  test_case_results: TestCaseResultItem[];
  compiler_output?: string;
  feedback?: string;
}

export const MockOARunnerPage: React.FC<MockOARunnerPageProps> = ({
  initialCompany = 'Google',
  initialRole = 'Software Engineer II (L4)',
  onNavigate
}) => {
  const [variant, setVariant] = useState<MockOAVariant | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // Multi-language code storage: questionId -> { [languageId]: code }
  const [codeByLang, setCodeByLang] = useState<Record<string, Record<string, string>>>({});
  // Selected language per question: questionId -> languageId
  const [selectedLangs, setSelectedLangs] = useState<Record<string, string>>({});
  
  // General answers (for MCQ, MSQ, or final submit): questionId -> answer
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [markedForReview, setMarkedForReview] = useState<Record<string, boolean>>({});
  const [timeSpent, setTimeSpent] = useState<Record<string, number>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirmSubmit, setShowConfirmSubmit] = useState(false);
  const [loading, setLoading] = useState(true);

  // Test Case Console state
  const [consoleTab, setConsoleTab] = useState<'testcases' | 'result'>('testcases');
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0);
  const [customInput, setCustomInput] = useState('');
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);

  // Autonomous anti-cheat proctoring
  const {
    integrityScore,
    integrityStatus,
    incidents,
    currentAlert,
    clearAlert,
    getProctoringSummary
  } = useProctoring({
    assessmentId: variant?.mock_oa_attempt_id,
    isEnabled: !loading && !isSubmitting && !!variant,
    warnOnTabSwitch: true,
    warnOnPaste: true,
    maxAllowedTabSwitches: 3
  });

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

  // Reset console result when switching questions
  useEffect(() => {
    setRunResult(null);
    setConsoleTab('testcases');
    setSelectedCaseIdx(0);
    setIsCustomMode(false);
  }, [currentIndex]);

  if (loading || !variant) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p>Acquiring canonical Assessment Set for {initialCompany} in active 7-day window...</p>
      </div>
    );
  }

  const currentQ: Question = variant.questions[currentIndex];
  const isCodingQuestion = !['MCQ', 'MSQ'].includes(currentQ.question_type.toUpperCase());
  
  // Determine current language for this question
  const currentLang = selectedLangs[currentQ.id] || (
    currentQ.question_type.toUpperCase() === 'SQL' ? 'sql' : 'cpp20'
  );

  // Determine current code for this question and language
  const currentCode = (codeByLang[currentQ.id] && codeByLang[currentQ.id][currentLang] !== undefined)
    ? codeByLang[currentQ.id][currentLang]
    : generateBoilerplate(currentLang, currentQ);

  // Non-coding answer (MCQ / MSQ)
  const nonCodingAnswer = answers[currentQ.id] ?? '';

  const handleCodeChange = (val: string) => {
    setCodeByLang(prev => ({
      ...prev,
      [currentQ.id]: {
        ...(prev[currentQ.id] || {}),
        [currentLang]: val
      }
    }));
    // Sync into answers for submit
    setAnswers(prev => ({
      ...prev,
      [currentQ.id]: {
        code: val,
        language: currentLang
      }
    }));
  };

  const handleLanguageChange = (newLang: string) => {
    setSelectedLangs(prev => ({ ...prev, [currentQ.id]: newLang }));

    // If no code exists yet for new language, generate proper boilerplate
    if (!codeByLang[currentQ.id] || codeByLang[currentQ.id][newLang] === undefined) {
      const boilerplate = generateBoilerplate(newLang, currentQ);
      setCodeByLang(prev => ({
        ...prev,
        [currentQ.id]: {
          ...(prev[currentQ.id] || {}),
          [newLang]: boilerplate
        }
      }));
      setAnswers(prev => ({
        ...prev,
        [currentQ.id]: {
          code: boilerplate,
          language: newLang
        }
      }));
    } else {
      setAnswers(prev => ({
        ...prev,
        [currentQ.id]: {
          code: codeByLang[currentQ.id][newLang],
          language: newLang
        }
      }));
    }
  };

  const handleNonCodingChange = (val: any) => {
    setAnswers(prev => ({ ...prev, [currentQ.id]: val }));
  };

  const toggleMarkForReview = () => {
    setMarkedForReview(prev => ({
      ...prev,
      [currentQ.id]: !prev[currentQ.id]
    }));
  };

  // Run code against test cases
  const handleRunCode = async () => {
    if (isRunningCode) return;
    setIsRunningCode(true);
    setConsoleTab('result');

    try {
      const res = await api.runCode({
        question_id: currentQ.id,
        code: currentCode,
        language: currentLang,
        custom_input: isCustomMode ? customInput : undefined
      });
      setRunResult(res);
      setSelectedCaseIdx(0);
    } catch (err: any) {
      setRunResult({
        status: 'RUNTIME_ERROR',
        runtime_ms: 0,
        memory_mb: 0,
        test_case_results: [],
        compiler_output: err.message || 'Execution request failed'
      });
    } finally {
      setIsRunningCode(false);
    }
  };

  const handleSubmitExam = async () => {
    setIsSubmitting(true);
    try {
      // Ensure all coding questions have their active code serialized
      const finalAnswers = { ...answers };
      for (const q of variant.questions) {
        if (!['MCQ', 'MSQ'].includes(q.question_type.toUpperCase())) {
          const lang = selectedLangs[q.id] || (q.question_type.toUpperCase() === 'SQL' ? 'sql' : 'cpp20');
          const code = (codeByLang[q.id] && codeByLang[q.id][lang]) || generateBoilerplate(lang, q);
          finalAnswers[q.id] = { code, language: lang };
        }
      }

      const report = await api.submitMockOA(variant.mock_oa_attempt_id, {
        answers: finalAnswers,
        time_spent_per_question: timeSpent,
        proctoring_data: getProctoringSummary()
      });
      onNavigate('oa-report', { report });
    } catch (err) {
      console.error(err);
      alert('Failed to submit assessment attempt.');
    } finally {
      setIsSubmitting(false);
      setShowConfirmSubmit(false);
    }
  };

  // Sample visible test cases
  const sampleTestCases = currentQ.test_cases || [];
  const answeredCount = Object.keys(answers).filter(k => answers[k] !== undefined && answers[k] !== '').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 relative">
      {/* Proctoring Warning Toast */}
      <ProctoringToast alert={currentAlert} onClose={clearAlert} />

      {/* Exam Banner Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/90 border border-white/10 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="px-3.5 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 font-mono text-xs font-bold tracking-wider">
            TIMED ASSESSMENT
          </div>
          <div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>{variant.company} • {variant.role}</span>
              <span className="text-xs text-slate-400 font-normal">
                (Assessment Set #{variant.attempt_number} • Window active for {variant.window_expires_in_days}d)
              </span>
            </div>
            <span className="text-xs text-slate-400">
              Standard timed conditions: External internet assistance and paste injection are monitored
            </span>
          </div>
        </div>

        {/* Proctoring, Timer & Submit Controls */}
        <div className="flex items-center gap-3">
          <ProctoringBadge
            integrityScore={integrityScore}
            integrityStatus={integrityStatus}
            incidents={incidents}
          />

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
            Submit Assessment
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className="grid lg:grid-cols-4 gap-6">
        {/* Left 3 Cols: Question, Editor and Console */}
        <div className="lg:col-span-3 space-y-4">
          {/* Question Description Card */}
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

          {/* Work Area: MCQ/MSQ Selection or Code Editor */}
          <div>
            {currentQ.question_type.toUpperCase() === 'MCQ' && currentQ.options ? (
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Select Answer Choice
                </div>
                {currentQ.options.map((opt, oIdx) => (
                  <label
                    key={oIdx}
                    onClick={() => handleNonCodingChange(opt)}
                    className={`block p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      nonCodingAnswer === opt
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
                  const curList: string[] = Array.isArray(nonCodingAnswer) ? nonCodingAnswer : [];
                  const isChecked = curList.includes(letter);

                  return (
                    <label
                      key={oIdx}
                      onClick={() => {
                        const next = isChecked ? curList.filter(x => x !== letter) : [...curList, letter];
                        handleNonCodingChange(next);
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
              <div className="space-y-4">
                {/* VS Code Monaco Editor */}
                <CodeEditor
                  value={currentCode}
                  onChange={handleCodeChange}
                  language={currentLang}
                  showLanguageSelector={true}
                  onLanguageChange={handleLanguageChange}
                  onReset={() => handleCodeChange(generateBoilerplate(currentLang, currentQ))}
                  onRunCode={handleRunCode}
                  isRunning={isRunningCode}
                  height="360px"
                />

                {/* HackerRank / LeetCode Interactive Testcase & Console Runner */}
                <div className="rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden shadow-xl">
                  {/* Console Header */}
                  <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-800/80 text-xs gap-3">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-indigo-400" />
                      <button
                        type="button"
                        onClick={() => setConsoleTab('testcases')}
                        className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                          consoleTab === 'testcases'
                            ? 'bg-slate-800 text-white shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Testcase
                      </button>
                      <button
                        type="button"
                        onClick={() => setConsoleTab('result')}
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-semibold transition-all ${
                          consoleTab === 'result'
                            ? 'bg-slate-800 text-white shadow-sm'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <span>Test Result</span>
                        {runResult && (
                          <span className={`w-2 h-2 rounded-full ${
                            runResult.status === 'ACCEPTED' ? 'bg-emerald-400' : 'bg-rose-400'
                          }`} />
                        )}
                      </button>
                    </div>

                    <div className="flex items-center gap-2 ml-auto">
                      <button
                        type="button"
                        onClick={handleRunCode}
                        disabled={isRunningCode}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold border border-slate-700 shadow-sm transition-all disabled:opacity-50"
                        title="Run Code against sample testcases (Ctrl+Enter)"
                      >
                        {isRunningCode ? (
                          <div className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        ) : (
                          <Play className="w-3.5 h-3.5 text-emerald-400 fill-current" />
                        )}
                        <span>{isRunningCode ? 'Running...' : 'Run Code'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Console Body */}
                  <div className="p-4 sm:p-5 space-y-4 min-h-[170px]">
                    {consoleTab === 'testcases' ? (
                      <div className="space-y-4">
                        {/* Testcase Selection Pills */}
                        <div className="flex flex-wrap items-center gap-2">
                          {sampleTestCases.map((_, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => {
                                setIsCustomMode(false);
                                setSelectedCaseIdx(idx);
                              }}
                              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                                !isCustomMode && selectedCaseIdx === idx
                                  ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                                  : 'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800'
                              }`}
                            >
                              Case {idx + 1}
                            </button>
                          ))}
                          <button
                            type="button"
                            onClick={() => setIsCustomMode(true)}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                              isCustomMode
                                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                                : 'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800'
                            }`}
                          >
                            + Custom Input
                          </button>
                        </div>

                        {/* Selected Case Content */}
                        {!isCustomMode && sampleTestCases[selectedCaseIdx] ? (
                          <div className="space-y-3">
                            <div>
                              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                                Input:
                              </div>
                              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800/80 font-mono text-xs text-slate-200">
                                {typeof sampleTestCases[selectedCaseIdx].input === 'object'
                                  ? JSON.stringify(sampleTestCases[selectedCaseIdx].input)
                                  : String(sampleTestCases[selectedCaseIdx].input)}
                              </div>
                            </div>

                            <div>
                              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                                Expected Output:
                              </div>
                              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800/80 font-mono text-xs text-emerald-400 font-semibold">
                                {String(sampleTestCases[selectedCaseIdx].expected_output)}
                              </div>
                            </div>
                          </div>
                        ) : isCustomMode ? (
                          <div className="space-y-2">
                            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                              Custom Input:
                            </div>
                            <textarea
                              value={customInput}
                              onChange={(e) => setCustomInput(e.target.value)}
                              placeholder="Enter your custom input parameters here..."
                              rows={3}
                              className="w-full p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 resize-y"
                            />
                          </div>
                        ) : (
                          <div className="text-xs text-slate-500 py-4">
                            No visible sample test cases available for this question. You can use Custom Input to test.
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Test Result Tab */
                      <div className="space-y-4">
                        {isRunningCode ? (
                          <div className="flex flex-col items-center justify-center py-8 space-y-3 text-slate-400 text-xs">
                            <div className="w-6 h-6 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
                            <span>Compiling and executing against test cases...</span>
                          </div>
                        ) : !runResult ? (
                          <div className="text-center py-8 text-slate-500 text-xs">
                            You must run your code first to see execution results. Click <span className="text-slate-300 font-semibold">Run Code</span>.
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {/* Headline Status Bar */}
                            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900 border border-slate-800">
                              <div className="flex items-center gap-2.5">
                                <span className={`px-3 py-1 rounded-lg text-xs font-bold tracking-wide flex items-center gap-1.5 ${
                                  runResult.status === 'ACCEPTED'
                                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                                    : runResult.status === 'COMPILATION_ERROR'
                                    ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                                    : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                                }`}>
                                  {runResult.status === 'ACCEPTED' ? (
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                  ) : (
                                    <X className="w-3.5 h-3.5 text-rose-400" />
                                  )}
                                  <span>{runResult.status.replace('_', ' ')}</span>
                                </span>
                                <span className="text-xs text-slate-400">
                                  {runResult.feedback}
                                </span>
                              </div>

                              <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
                                <span>Runtime: <strong className="text-slate-200">{runResult.runtime_ms} ms</strong></span>
                                <span>•</span>
                                <span>Memory: <strong className="text-slate-200">{runResult.memory_mb} MB</strong></span>
                              </div>
                            </div>

                            {/* Compiler Output / Error */}
                            {runResult.compiler_output && runResult.status !== 'ACCEPTED' && (
                              <div className="space-y-1.5">
                                <div className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider">
                                  Compiler Message / Error Output:
                                </div>
                                <pre className="p-3 rounded-xl bg-slate-950 border border-rose-900/50 font-mono text-[11px] text-rose-300 whitespace-pre-wrap overflow-x-auto leading-relaxed">
                                  {runResult.compiler_output}
                                </pre>
                              </div>
                            )}

                            {/* Test Cases Results Breakdown */}
                            {runResult.test_case_results && runResult.test_case_results.length > 0 && (
                              <div className="space-y-3">
                                <div className="flex flex-wrap items-center gap-2">
                                  {runResult.test_case_results.map((tc, idx) => (
                                    <button
                                      key={idx}
                                      type="button"
                                      onClick={() => setSelectedCaseIdx(idx)}
                                      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                                        selectedCaseIdx === idx
                                          ? 'bg-slate-800 text-white border border-slate-700 shadow-sm'
                                          : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                                      }`}
                                    >
                                      <span className={`w-2 h-2 rounded-full ${tc.passed ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                                      <span>Case {idx + 1}</span>
                                    </button>
                                  ))}
                                </div>

                                {runResult.test_case_results[selectedCaseIdx] && (
                                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-3 text-xs">
                                    <div>
                                      <div className="text-[11px] text-slate-400 font-semibold uppercase mb-1">Input:</div>
                                      <div className="p-2.5 rounded-lg bg-slate-950 font-mono text-slate-200">
                                        {runResult.test_case_results[selectedCaseIdx].input_data}
                                      </div>
                                    </div>

                                    <div>
                                      <div className="text-[11px] text-slate-400 font-semibold uppercase mb-1">Expected Output:</div>
                                      <div className="p-2.5 rounded-lg bg-slate-950 font-mono text-emerald-400">
                                        {runResult.test_case_results[selectedCaseIdx].expected_output}
                                      </div>
                                    </div>

                                    <div>
                                      <div className="text-[11px] text-slate-400 font-semibold uppercase mb-1">Your Output:</div>
                                      <div className={`p-2.5 rounded-lg bg-slate-950 font-mono ${
                                        runResult.test_case_results[selectedCaseIdx].passed ? 'text-emerald-400' : 'text-rose-400'
                                      }`}>
                                        {runResult.test_case_results[selectedCaseIdx].actual_output}
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
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
              <span className="font-mono text-brand-400">{answeredCount}/{variant.questions.length} Attempted</span>
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
                    className={`h-11 rounded-xl text-xs font-bold font-mono transition-all flex flex-col items-center justify-center relative ${
                      isCurrent
                        ? 'ring-2 ring-brand-500 bg-brand-600 text-white shadow-lg shadow-brand-500/25'
                        : isAnswered
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 hover:bg-emerald-900/80'
                        : isFlagged
                        ? 'bg-amber-950/80 text-amber-300 border border-amber-800/80'
                        : 'bg-slate-950/80 text-slate-400 border border-slate-800 hover:bg-slate-800/80'
                    }`}
                  >
                    <span>{idx + 1}</span>
                    {isFlagged && (
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 absolute top-1 right-1" />
                    )}
                  </button>
                );
              })}
            </div>

            <div className="pt-3 border-t border-slate-800 space-y-2 text-[11px] text-slate-400">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-emerald-950 border border-emerald-700" />
                <span>Attempted</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-brand-600" />
                <span>Current Question</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-amber-950 border border-amber-700" />
                <span>Marked for Review</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-slate-950 border border-slate-800" />
                <span>Unattempted</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal for Exam Submission */}
      {showConfirmSubmit && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl space-y-5">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Submit Online Assessment?</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              You have answered <strong className="text-white">{answeredCount}</strong> out of{' '}
              <strong className="text-white">{variant.questions.length}</strong> questions.
              Once submitted, all coding solutions and selections will be deterministically scored against standard test cases.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmSubmit(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Continue Assessment
              </button>

              <button
                type="button"
                onClick={handleSubmitExam}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-lg shadow-emerald-600/25 transition-all disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                    <span>Scoring OA Attempt...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Confirm & Finish</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
