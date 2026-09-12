import React, { useState, useEffect } from 'react';
import { 
  Clock, AlertCircle, CheckCircle2, ChevronLeft, ChevronRight,
  Send, Flag, Code2, AlertTriangle, Play, Terminal, 
  Check, X, Sparkles, RefreshCw, ChevronUp, ChevronDown, Lightbulb, Loader2
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

interface ParsedExample {
  title: string;
  input: string;
  output: string;
  explanation?: string;
}

function parseProblemPrompt(prompt: string, fallbackTestCases?: any[]) {
  const exampleRegex = /###\s*(Example\s*\d+):?\s*([\s\S]*?)(?=(###\s*Example|###\s*Constraints|$))/gi;
  const constraintsRegex = /###\s*Constraints:?\s*([\s\S]*?)$/i;

  const examples: ParsedExample[] = [];
  let match;
  while ((match = exampleRegex.exec(prompt)) !== null) {
    const title = match[1];
    const content = match[2];
    
    const inputMatch = content.match(/\*\*Input:\*\*\s*(`[^`]+`|[^\n]+)|Input:\s*([^\n]+)/i);
    const outputMatch = content.match(/\*\*Output:\*\*\s*(`[^`]+`|[^\n]+)|Output:\s*([^\n]+)/i);
    const explMatch = content.match(/\*\*Explanation:\*\*\s*([\s\S]*?)$|Explanation:\s*([\s\S]*?)$/i);

    const input = (inputMatch?.[1] || inputMatch?.[2] || '').replace(/^`|`$/g, '').trim();
    const output = (outputMatch?.[1] || outputMatch?.[2] || '').replace(/^`|`$/g, '').trim();
    const explanation = (explMatch?.[1] || explMatch?.[2] || '').trim();

    examples.push({ title, input, output, explanation });
  }

  // If no examples parsed from markdown, use test cases
  if (examples.length === 0 && fallbackTestCases && fallbackTestCases.length > 0) {
    fallbackTestCases.slice(0, 3).forEach((tc, i) => {
      examples.push({
        title: `Example ${i + 1}`,
        input: typeof tc.input === 'object' ? JSON.stringify(tc.input) : String(tc.input),
        output: String(tc.expected_output),
        explanation: ''
      });
    });
  }

  const constraintsMatch = prompt.match(constraintsRegex);
  let constraints: string[] = [];
  if (constraintsMatch && constraintsMatch[1]) {
    constraints = constraintsMatch[1]
      .split('\n')
      .map(c => c.replace(/^[-*•]\s*/, '').trim())
      .filter(c => c.length > 0);
  }

  if (constraints.length === 0) {
    constraints = [
      'Time Limit: 2.0 seconds',
      'Memory Limit: 256 MB',
      'Standard DSA execution bounds apply'
    ];
  }

  const firstHeaderIdx = prompt.search(/###\s*(Example|Constraints)/i);
  const baseDescription = firstHeaderIdx !== -1 ? prompt.substring(0, firstHeaderIdx).trim() : prompt.trim();

  return { baseDescription, examples, constraints };
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

  // Left panel view tabs
  const [leftTab, setLeftTab] = useState<'description' | 'hints'>('description');

  // Test Case Console state
  const [consoleTab, setConsoleTab] = useState<'testcases' | 'result'>('testcases');
  const [isConsoleExpanded, setIsConsoleExpanded] = useState(true);
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
    setLeftTab('description');
  }, [currentIndex]);

  if (loading || !variant) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm font-medium">Acquiring verified Assessment Set for {initialCompany}...</p>
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

  const nonCodingAnswer = answers[currentQ.id] || null;

  const handleCodeChange = (val: string) => {
    setCodeByLang(prev => ({
      ...prev,
      [currentQ.id]: {
        ...(prev[currentQ.id] || {}),
        [currentLang]: val
      }
    }));
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
    setIsConsoleExpanded(true);

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
      console.error('Submission failed:', err);
    } finally {
      setIsSubmitting(false);
      setShowConfirmSubmit(false);
    }
  };

  const answeredCount = Object.keys(answers).filter(k => {
    const val = answers[k];
    if (!val) return false;
    if (typeof val === 'object' && val.code !== undefined) {
      return val.code.trim().length > 25;
    }
    return true;
  }).length;

  const { baseDescription, examples, constraints } = parseProblemPrompt(currentQ.prompt, currentQ.test_cases);
  const sampleCases = currentQ.test_cases || [];

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-slate-950 font-sans select-none">
      {/* Real-time Proctoring Toast notification */}
      {currentAlert && (
        <ProctoringToast alert={currentAlert} onClose={clearAlert} />
      )}

      {/* TOP BAR: Header, Question Selector, Timer, Submit */}
      <header className="h-14 shrink-0 px-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs gap-4 z-20">
        {/* Left: Brand / Role and Question Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 pr-3 border-r border-slate-800">
            <span className="font-bold text-white tracking-wide text-xs sm:text-sm">
              {variant.company}
            </span>
            <span className="hidden md:inline text-slate-400 text-xs">
              • {variant.role}
            </span>
          </div>

          {/* Question Nav Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
            <button
              onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
              disabled={currentIndex === 0}
              className="p-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              title="Previous Question"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            {variant.questions.map((q, idx) => {
              const isCurrent = idx === currentIndex;
              const isFlagged = markedForReview[q.id];
              const ans = answers[q.id];
              const isAnswered = ans && (typeof ans !== 'object' || (ans.code && ans.code.trim().length > 25));

              return (
                <button
                  key={q.id}
                  onClick={() => setCurrentIndex(idx)}
                  className={`w-7 h-7 rounded-lg font-mono font-bold text-xs flex items-center justify-center relative transition-all ${
                    isCurrent
                      ? 'bg-indigo-600 text-white ring-2 ring-indigo-400 shadow-md shadow-indigo-500/30 font-extrabold'
                      : isAnswered
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-700/80 hover:bg-emerald-900'
                      : isFlagged
                      ? 'bg-amber-950 text-amber-300 border border-amber-700'
                      : 'bg-slate-800/80 text-slate-400 border border-slate-700 hover:bg-slate-700'
                  }`}
                  title={`Question ${idx + 1}: ${q.title || q.subtopic}`}
                >
                  <span>{idx + 1}</span>
                  {isFlagged && (
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 absolute -top-0.5 -right-0.5" />
                  )}
                </button>
              );
            })}

            <button
              onClick={() => setCurrentIndex(Math.min(variant.questions.length - 1, currentIndex + 1))}
              disabled={currentIndex === variant.questions.length - 1}
              className="p-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              title="Next Question"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Center: Timer */}
        <div className="flex items-center gap-2">
          <Timer
            initialMinutes={variant.duration_minutes}
            onTimeExpired={handleSubmitExam}
            isRunning={true}
          />
        </div>

        {/* Right: Proctoring Integrity & Submit Button */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <ProctoringBadge
              integrityScore={integrityScore}
              integrityStatus={integrityStatus}
              incidents={incidents}
            />
          </div>

          <button
            onClick={() => setShowConfirmSubmit(true)}
            className="px-3.5 py-1.5 rounded-xl font-bold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all text-xs"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Submit</span>
          </button>
        </div>
      </header>

      {/* MAIN BODY: TRUE 50/50 SPLIT SCREEN (LeetCode Layout) */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-2 p-2 overflow-hidden bg-slate-950">
        
        {/* ============================================================ */}
        {/* LEFT PANEL: Problem Description, Examples, Constraints, Hint */}
        {/* ============================================================ */}
        <div className="h-full flex flex-col rounded-2xl border border-slate-800/90 bg-slate-900/90 shadow-xl overflow-hidden">
          {/* Problem Header Tabs */}
          <div className="px-4 py-2 bg-slate-950/70 border-b border-slate-800/80 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setLeftTab('description')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  leftTab === 'description'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Description
              </button>
              {currentQ.hint && (
                <button
                  type="button"
                  onClick={() => setLeftTab('hints')}
                  className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    leftTab === 'hints'
                      ? 'bg-slate-800 text-amber-300 shadow-sm'
                      : 'text-slate-400 hover:text-amber-200'
                  }`}
                >
                  <Lightbulb className="w-3 h-3 text-amber-400" />
                  <span>Hints</span>
                </button>
              )}
            </div>

            <button
              onClick={toggleMarkForReview}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                markedForReview[currentQ.id]
                  ? 'bg-amber-950 text-amber-300 border border-amber-700'
                  : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Flag className="w-3.5 h-3.5" />
              <span>{markedForReview[currentQ.id] ? 'Marked' : 'Mark for Review'}</span>
            </button>
          </div>

          {/* Problem Content (Scrollable) */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5 text-slate-200">
            {leftTab === 'description' ? (
              <>
                {/* Title & Metadata Badges */}
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-indigo-950 text-indigo-300 border border-indigo-800">
                      {currentQ.question_type}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                      currentQ.difficulty.toLowerCase() === 'hard'
                        ? 'bg-rose-950 text-rose-300 border border-rose-800'
                        : currentQ.difficulty.toLowerCase() === 'easy'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}>
                      {currentQ.difficulty}
                    </span>
                    <span className="text-xs text-slate-400">
                      {currentQ.topic}
                    </span>
                  </div>

                  <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                    {currentIndex + 1}. {currentQ.title || currentQ.subtopic}
                  </h1>
                </div>

                {/* Base Problem Description */}
                <div className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-line">
                  {baseDescription}
                </div>

                {/* Structured Examples Section (LeetCode Style) */}
                {examples.length > 0 && (
                  <div className="space-y-4 pt-2">
                    {examples.map((ex, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2 shadow-inner"
                      >
                        <div className="text-xs font-bold text-slate-200">
                          {ex.title}:
                        </div>

                        {ex.input && (
                          <div className="flex items-start gap-2 text-xs">
                            <span className="font-semibold text-slate-400 shrink-0">Input:</span>
                            <code className="font-mono text-amber-300/90 break-all">
                              {ex.input}
                            </code>
                          </div>
                        )}

                        {ex.output && (
                          <div className="flex items-start gap-2 text-xs">
                            <span className="font-semibold text-slate-400 shrink-0">Output:</span>
                            <code className="font-mono text-emerald-400 break-all">
                              {ex.output}
                            </code>
                          </div>
                        )}

                        {ex.explanation && (
                          <div className="flex items-start gap-2 text-xs pt-1 border-t border-slate-800/60 text-slate-400">
                            <span className="font-semibold shrink-0">Explanation:</span>
                            <span>{ex.explanation}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Constraints Section */}
                {constraints.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Constraints:
                    </h3>
                    <ul className="space-y-1.5 pl-2">
                      {constraints.map((c, i) => (
                        <li key={i} className="flex items-center gap-2 text-xs text-slate-300">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                          <code className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-indigo-300">
                            {c}
                          </code>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              /* Hints Tab */
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/50 space-y-2">
                  <div className="flex items-center gap-2 text-amber-300 font-bold text-xs">
                    <Lightbulb className="w-4 h-4" />
                    <span>Algorithmic Hint</span>
                  </div>
                  <p className="text-xs text-amber-200/90 leading-relaxed font-sans">
                    {currentQ.hint}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ============================================================ */}
        {/* RIGHT PANEL: Monaco Code Editor + Testcase & Console Runner */}
        {/* ============================================================ */}
        <div className="h-full flex flex-col rounded-2xl border border-slate-800/90 bg-slate-900/90 shadow-xl overflow-hidden">
          {/* If MCQ / MSQ: Render Multiple Choice Options */}
          {!isCodingQuestion ? (
            <div className="p-6 flex-1 overflow-y-auto space-y-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                {currentQ.question_type.toUpperCase() === 'MCQ' ? 'Select One Option:' : 'Select All Applicable Choices (MSQ):'}
              </div>

              {currentQ.options?.map((opt, oIdx) => {
                const letter = opt.trim().slice(0, 1);
                const isChecked = currentQ.question_type.toUpperCase() === 'MCQ'
                  ? nonCodingAnswer === opt
                  : Array.isArray(nonCodingAnswer) && nonCodingAnswer.includes(letter);

                return (
                  <label
                    key={oIdx}
                    onClick={() => {
                      if (currentQ.question_type.toUpperCase() === 'MCQ') {
                        handleNonCodingChange(opt);
                      } else {
                        const curList: string[] = Array.isArray(nonCodingAnswer) ? nonCodingAnswer : [];
                        const next = isChecked ? curList.filter(x => x !== letter) : [...curList, letter];
                        handleNonCodingChange(next);
                      }
                    }}
                    className={`block p-4 rounded-xl border text-xs cursor-pointer transition-all ${
                      isChecked
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 font-semibold shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60'
                    }`}
                  >
                    {opt}
                  </label>
                );
              })}
            </div>
          ) : (
            /* Coding Problem: Editor on top + Console on bottom */
            <>
              {/* TOP: Monaco Code Editor */}
              <div className="flex-1 min-h-[300px] flex flex-col overflow-hidden">
                <CodeEditor
                  value={currentCode}
                  onChange={handleCodeChange}
                  language={currentLang}
                  showLanguageSelector={true}
                  onLanguageChange={handleLanguageChange}
                  onReset={() => handleCodeChange(generateBoilerplate(currentLang, currentQ))}
                  onRunCode={handleRunCode}
                  isRunning={isRunningCode}
                  height="100%"
                />
              </div>

              {/* BOTTOM: LeetCode-style Testcase & Console Runner */}
              <div
                className={`flex flex-col border-t border-slate-800 bg-slate-950 transition-all ${
                  isConsoleExpanded ? 'h-[280px]' : 'h-10'
                }`}
              >
                {/* Console Header */}
                <div className="h-10 shrink-0 px-4 bg-slate-900 border-b border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setIsConsoleExpanded(!isConsoleExpanded)}
                      className="text-slate-400 hover:text-white p-1 rounded transition-colors"
                      title={isConsoleExpanded ? 'Collapse Console' : 'Expand Console'}
                    >
                      {isConsoleExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
                    </button>

                    <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                    
                    <button
                      type="button"
                      onClick={() => { setConsoleTab('testcases'); setIsConsoleExpanded(true); }}
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
                      onClick={() => { setConsoleTab('result'); setIsConsoleExpanded(true); }}
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

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleRunCode}
                      disabled={isRunningCode}
                      className="px-3.5 py-1.5 rounded-xl font-bold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 shadow-md shadow-indigo-600/20 disabled:opacity-50 transition-all text-xs"
                    >
                      {isRunningCode ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Running...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-current" />
                          <span>Run Code</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Console Body */}
                {isConsoleExpanded && (
                  <div className="flex-1 overflow-y-auto p-4 text-xs font-mono">
                    {consoleTab === 'testcases' ? (
                      /* Testcases Tab */
                      <div className="space-y-3">
                        {/* Case Switcher */}
                        <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5">
                          {sampleCases.map((_, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => { setSelectedCaseIdx(idx); setIsCustomMode(false); }}
                              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                                !isCustomMode && selectedCaseIdx === idx
                                  ? 'bg-slate-800 text-white'
                                  : 'text-slate-400 hover:text-slate-200'
                              }`}
                            >
                              Case {idx + 1}
                            </button>
                          ))}

                          <button
                            type="button"
                            onClick={() => setIsCustomMode(true)}
                            className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                              isCustomMode
                                ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50'
                                : 'text-slate-400 hover:text-slate-200'
                            }`}
                          >
                            + Custom Input
                          </button>
                        </div>

                        {/* Case Details */}
                        {!isCustomMode ? (
                          sampleCases[selectedCaseIdx] ? (
                            <div className="space-y-2">
                              <div className="text-[11px] text-slate-400 uppercase font-bold">Input:</div>
                              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-amber-300 break-all">
                                {typeof sampleCases[selectedCaseIdx].input === 'object'
                                  ? JSON.stringify(sampleCases[selectedCaseIdx].input)
                                  : String(sampleCases[selectedCaseIdx].input)}
                              </div>

                              <div className="text-[11px] text-slate-400 uppercase font-bold pt-1">Expected:</div>
                              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-emerald-400 break-all">
                                {String(sampleCases[selectedCaseIdx].expected_output)}
                              </div>
                            </div>
                          ) : (
                            <div className="text-slate-500">No testcase selected.</div>
                          )
                        ) : (
                          /* Custom Input Editor */
                          <div className="space-y-2">
                            <div className="text-[11px] text-slate-400 uppercase font-bold">
                              Enter Custom Parameter(s):
                            </div>
                            <textarea
                              value={customInput}
                              onChange={e => setCustomInput(e.target.value)}
                              placeholder="e.g. [1, 2, 5], 11 or &quot;abcabcbb&quot;"
                              className="w-full h-24 p-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-600 font-mono text-xs focus:outline-none focus:border-indigo-500"
                            />
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Test Result Tab */
                      <div>
                        {isRunningCode ? (
                          <div className="flex items-center gap-2.5 text-slate-400 py-8 justify-center">
                            <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                            <span>Compiling and executing test cases...</span>
                          </div>
                        ) : runResult ? (
                          <div className="space-y-3">
                            {/* Status Header */}
                            <div className="flex items-center gap-3">
                              <span className={`text-base font-bold ${
                                runResult.status === 'ACCEPTED' ? 'text-emerald-400' : 'text-rose-400'
                              }`}>
                                {runResult.status === 'ACCEPTED' ? 'Accepted' :
                                 runResult.status === 'WRONG_ANSWER' ? 'Wrong Answer' :
                                 runResult.status === 'COMPILATION_ERROR' ? 'Compilation Error' :
                                 runResult.status === 'RUNTIME_ERROR' ? 'Runtime Error' : 'Time Limit Exceeded'}
                              </span>

                              <span className="text-slate-400 text-xs">
                                Runtime: <strong className="text-white">{runResult.runtime_ms} ms</strong>
                              </span>
                              <span className="text-slate-400 text-xs">
                                Memory: <strong className="text-white">{runResult.memory_mb} MB</strong>
                              </span>
                            </div>

                            {/* Compiler stderr if any */}
                            {runResult.compiler_output && (
                              <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-800/50 text-rose-300 whitespace-pre-wrap">
                                {runResult.compiler_output}
                              </div>
                            )}

                            {/* Test Cases Results Switcher */}
                            {runResult.test_case_results?.length > 0 && (
                              <>
                                <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                                  {runResult.test_case_results.map((tc, idx) => (
                                    <button
                                      key={idx}
                                      type="button"
                                      onClick={() => setSelectedCaseIdx(idx)}
                                      className={`flex items-center gap-1.5 px-3 py-1 rounded-lg font-semibold transition-all ${
                                        selectedCaseIdx === idx
                                          ? 'bg-slate-800 text-white'
                                          : 'text-slate-400 hover:text-slate-200'
                                      }`}
                                    >
                                      <span className={`w-2 h-2 rounded-full ${tc.passed ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                                      <span>Case {idx + 1}</span>
                                    </button>
                                  ))}
                                </div>

                                {runResult.test_case_results[selectedCaseIdx] && (
                                  <div className="space-y-2 pt-1">
                                    <div className="text-[11px] text-slate-400 uppercase font-bold">Input:</div>
                                    <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 break-all">
                                      {runResult.test_case_results[selectedCaseIdx].input_data}
                                    </div>

                                    <div className="text-[11px] text-slate-400 uppercase font-bold">Your Output:</div>
                                    <div className={`p-2.5 rounded-xl border break-all ${
                                      runResult.test_case_results[selectedCaseIdx].passed
                                        ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-400'
                                        : 'bg-rose-950/20 border-rose-800/60 text-rose-400'
                                    }`}>
                                      {runResult.test_case_results[selectedCaseIdx].actual_output}
                                    </div>

                                    <div className="text-[11px] text-slate-400 uppercase font-bold">Expected Output:</div>
                                    <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-emerald-400 break-all">
                                      {runResult.test_case_results[selectedCaseIdx].expected_output}
                                    </div>
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        ) : (
                          <div className="text-slate-500 py-6 text-center">
                            Click &quot;Run Code&quot; to execute your solution against test cases.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </main>

      {/* Confirmation Modal for Exam Submission */}
      {showConfirmSubmit && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-2xl space-y-5">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Submit Online Assessment?</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              You have answered <strong className="text-white">{answeredCount}</strong> out of{' '}
              <strong className="text-white">{variant.questions.length}</strong> questions.
              Once submitted, all coding solutions will be graded deterministically across all standard and hidden test cases.
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
                    <span>Grading Assessment...</span>
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
