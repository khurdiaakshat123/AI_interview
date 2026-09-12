import React, { useState, useEffect, useRef } from 'react';
import { 
  Clock, AlertCircle, CheckCircle2, ChevronLeft, ChevronRight,
  Send, Flag, Code2, AlertTriangle, Play, Terminal, 
  Check, X, Sparkles, RotateCcw, ChevronUp, ChevronDown, Lightbulb, Loader2,
  Upload, Maximize2, Minimize2, FileCode, Award, MessageSquare, History,
  BookOpen, HelpCircle
} from 'lucide-react';
import { MockOAVariant, Question } from '../types';
import { Timer } from '../components/Timer';
import { CodeEditor, EDITOR_THEMES } from '../components/CodeEditor';
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

interface SubmissionRecord {
  id: string;
  timestamp: string;
  language: string;
  status: string;
  passedCount: number;
  totalCount: number;
  runtimeMs: number;
  memoryMb: number;
}

interface ParsedExample {
  title: string;
  input: string;
  output: string;
  explanation?: string;
}

function parseProblemPrompt(prompt: string, fallbackTestCases?: any[]) {
  const exampleRegex = /###\s*(Example\s*\d*|Sample\s*Input|Sample\s*Case\s*\d*):?\s*([\s\S]*?)(?=(###\s*(Example|Constraints|Function|Returns|Input|Sample)|$))/gi;
  const constraintsRegex = /###\s*Constraints:?\s*([\s\S]*?)(?=(###|$))/i;

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

    if (input || output) {
      examples.push({ title, input, output, explanation });
    }
  }

  // If no examples parsed from markdown headers, use test cases
  if (examples.length === 0 && fallbackTestCases && fallbackTestCases.length > 0) {
    fallbackTestCases.slice(0, 3).forEach((tc, i) => {
      examples.push({
        title: `Sample Case ${i}`,
        input: typeof tc.input === 'object' ? JSON.stringify(tc.input, null, 2) : String(tc.input),
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

  const firstHeaderIdx = prompt.search(/###\s*(Example|Constraints|Function|Returns|Input Format|Sample)/i);
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

  // HackerRank Left Rail Navigation: 'problem' | 'submissions' | 'leaderboard' | 'discussions'
  const [activeRailTab, setActiveRailTab] = useState<'problem' | 'submissions' | 'leaderboard' | 'discussions'>('problem');

  // Submissions history for this session
  const [submissionsHistory, setSubmissionsHistory] = useState<Record<string, SubmissionRecord[]>>({});

  // Monaco Editor settings
  const [editorTheme, setEditorTheme] = useState('vs-dark');
  const [cursorPosition, setCursorPosition] = useState({ line: 1, col: 1 });
  const [isFullScreenView, setIsFullScreenView] = useState(false);

  // Test Case Console / Bottom Drawer state
  const [isConsoleExpanded, setIsConsoleExpanded] = useState(false);
  const [selectedCaseIdx, setSelectedCaseIdx] = useState(0);
  const [testAgainstCustomInput, setTestAgainstCustomInput] = useState(false);
  const [customInputText, setCustomInputText] = useState('');
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [runResult, setRunResult] = useState<RunResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
    setSelectedCaseIdx(0);
    setTestAgainstCustomInput(false);
    setActiveRailTab('problem');
  }, [currentIndex]);

  if (loading || !variant) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-24 text-center text-slate-400">
        <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm font-semibold text-slate-200">Starting HackerRank Online Assessment Environment...</p>
        <p className="text-xs text-slate-500 mt-1">Preparing compiler runners, isolated test sandboxes, and question set.</p>
      </div>
    );
  }

  const currentQ: Question = variant.questions[currentIndex];
  const isCodingQuestion = !['MCQ', 'MSQ'].includes(currentQ.question_type.toUpperCase());
  
  // Default language: C++20 for DSA, SQL for Database
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

  const handleResetCode = () => {
    const boilerplate = generateBoilerplate(currentLang, currentQ);
    handleCodeChange(boilerplate);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === 'string') {
        handleCodeChange(content);
      }
    };
    reader.readAsText(file);
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

  // Run code against test cases (or custom input)
  const handleRunCode = async () => {
    if (isRunningCode) return;
    setIsRunningCode(true);
    setIsConsoleExpanded(true);

    try {
      const res = await api.runCode({
        question_id: currentQ.id,
        code: currentCode,
        language: currentLang,
        custom_input: testAgainstCustomInput ? customInputText : undefined
      });
      setRunResult(res);
      setSelectedCaseIdx(0);

      // Record in session submission history
      const passedCount = res.test_case_results?.filter((r: any) => r.passed).length || 0;
      const totalCount = res.test_case_results?.length || 0;
      const newRecord: SubmissionRecord = {
        id: `run-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        language: currentLang,
        status: res.status,
        passedCount,
        totalCount,
        runtimeMs: res.runtime_ms,
        memoryMb: res.memory_mb
      };
      setSubmissionsHistory(prev => ({
        ...prev,
        [currentQ.id]: [newRecord, ...(prev[currentQ.id] || [])]
      }));
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
    <div className={`flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-[#0d1117] text-slate-200 font-sans select-none ${
      isFullScreenView ? 'fixed inset-0 z-50 h-screen' : 'relative'
    }`}>
      {/* Real-time Proctoring Toast notification */}
      {currentAlert && (
        <ProctoringToast alert={currentAlert} onClose={clearAlert} />
      )}

      {/* ============================================================ */}
      {/* HACKERRANK TOP BAR: Logo, Breadcrumbs, Timer, Fullscreen, Submit */}
      {/* ============================================================ */}
      <header className="h-12 shrink-0 px-4 bg-[#161f28] border-b border-[#2d3a4b] flex items-center justify-between text-xs gap-4 z-20">
        {/* Left: HackerRank Logo & Breadcrumbs */}
        <div className="flex items-center gap-3 overflow-hidden">
          {/* HackerRank Icon & Text */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-6 h-6 rounded bg-[#1BA94C] flex items-center justify-center font-black text-white text-sm shadow-sm">
              H
            </div>
            <span className="font-extrabold text-white text-sm tracking-tight hidden sm:inline">
              HackerRank
            </span>
          </div>

          <span className="text-slate-600 font-light">|</span>

          {/* Breadcrumbs */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium truncate">
            <span className="hover:text-slate-200 cursor-pointer hidden md:inline">Prepare</span>
            <span className="text-slate-600 hidden md:inline">&gt;</span>
            <span className="hover:text-slate-200 cursor-pointer hidden sm:inline">Data Structures</span>
            <span className="text-slate-600 hidden sm:inline">&gt;</span>
            <span className="hover:text-slate-200 cursor-pointer">{currentQ.topic || 'Arrays'}</span>
            <span className="text-slate-600">&gt;</span>
            <span className="text-emerald-400 font-semibold truncate">
              {currentQ.title || '2D Array - DS'}
            </span>
          </div>
        </div>

        {/* Center: Question Navigation Pills */}
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
            disabled={currentIndex === 0}
            className="p-1 rounded bg-[#212e3c] hover:bg-[#2c3d4f] text-slate-300 disabled:opacity-30 disabled:pointer-events-none transition-colors"
            title="Previous Question"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>

          <span className="text-[11px] font-mono text-slate-400 px-1.5">
            {currentIndex + 1} / {variant.questions.length}
          </span>

          <button
            onClick={() => setCurrentIndex(Math.min(variant.questions.length - 1, currentIndex + 1))}
            disabled={currentIndex === variant.questions.length - 1}
            className="p-1 rounded bg-[#212e3c] hover:bg-[#2c3d4f] text-slate-300 disabled:opacity-30 disabled:pointer-events-none transition-colors"
            title="Next Question"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Right: Timer, Full Screen Toggle, Proctoring, Finish Exam */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Active Timer */}
          <div className="flex items-center gap-1.5 bg-[#212e3c] px-2.5 py-1 rounded text-slate-200 font-mono text-xs border border-slate-700/50">
            <Clock className="w-3.5 h-3.5 text-emerald-400" />
            <Timer
              initialMinutes={variant.duration_minutes}
              onTimeExpired={handleSubmitExam}
              isRunning={true}
            />
          </div>

          {/* Exit / Enter Full Screen View */}
          <button
            type="button"
            onClick={() => setIsFullScreenView(!isFullScreenView)}
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#212e3c] hover:bg-[#2c3d4f] text-slate-300 hover:text-white text-[11px] transition-colors border border-slate-700/50"
            title="Toggle Full Screen View"
          >
            {isFullScreenView ? (
              <>
                <Minimize2 className="w-3 h-3 text-emerald-400" />
                <span>Exit Full Screen</span>
              </>
            ) : (
              <>
                <Maximize2 className="w-3 h-3 text-slate-400" />
                <span>Full Screen View</span>
              </>
            )}
          </button>

          {/* Proctoring Badge */}
          <div className="hidden xl:block">
            <ProctoringBadge
              integrityScore={integrityScore}
              integrityStatus={integrityStatus}
              incidents={incidents}
            />
          </div>

          {/* Submit Assessment Button */}
          <button
            type="button"
            onClick={() => setShowConfirmSubmit(true)}
            className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs border border-slate-700 transition-all"
          >
            Finish Exam
          </button>
        </div>
      </header>

      {/* ============================================================ */}
      {/* MAIN CONTAINER: LEFT VERTICAL RAIL + PROBLEM AREA + CODE EDITOR */}
      {/* ============================================================ */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* ============================================================ */}
        {/* LEFT VERTICAL RAIL (HackerRank Tabs: Problem, Submissions, etc.) */}
        {/* ============================================================ */}
        <aside className="w-12 shrink-0 bg-[#161f28] border-r border-[#2d3a4b] flex flex-col items-center py-3 gap-4 z-10 select-none">
          <button
            type="button"
            onClick={() => setActiveRailTab('problem')}
            className={`w-9 h-9 rounded flex items-center justify-center transition-all ${
              activeRailTab === 'problem'
                ? 'bg-[#1BA94C] text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-white hover:bg-[#212e3c]'
            }`}
            title="Problem Statement"
          >
            <BookOpen className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setActiveRailTab('submissions')}
            className={`w-9 h-9 rounded flex items-center justify-center transition-all ${
              activeRailTab === 'submissions'
                ? 'bg-[#1BA94C] text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-white hover:bg-[#212e3c]'
            }`}
            title="Submissions"
          >
            <History className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setActiveRailTab('leaderboard')}
            className={`w-9 h-9 rounded flex items-center justify-center transition-all ${
              activeRailTab === 'leaderboard'
                ? 'bg-[#1BA94C] text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-white hover:bg-[#212e3c]'
            }`}
            title="Leaderboard"
          >
            <Award className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setActiveRailTab('discussions')}
            className={`w-9 h-9 rounded flex items-center justify-center transition-all ${
              activeRailTab === 'discussions'
                ? 'bg-[#1BA94C] text-white shadow-sm font-bold'
                : 'text-slate-400 hover:text-white hover:bg-[#212e3c]'
            }`}
            title="Discussions"
          >
            <MessageSquare className="w-4 h-4" />
          </button>

          <div className="mt-auto flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={toggleMarkForReview}
              className={`w-9 h-9 rounded flex items-center justify-center transition-all ${
                markedForReview[currentQ.id]
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                  : 'text-slate-400 hover:text-white hover:bg-[#212e3c]'
              }`}
              title={markedForReview[currentQ.id] ? 'Flagged for Review' : 'Mark for Review'}
            >
              <Flag className="w-4 h-4" />
            </button>
          </div>
        </aside>

        {/* ============================================================ */}
        {/* TRUE 50/50 SPLIT SCREEN: LEFT PROBLEM + RIGHT EDITOR */}
        {/* ============================================================ */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 overflow-hidden">

          {/* ============================================================ */}
          {/* LEFT AREA: Problem Statement & HackerRank Structured Sections */}
          {/* ============================================================ */}
          <section className="h-full flex flex-col border-r border-[#2d3a4b] bg-[#101720] overflow-hidden">
            {/* Header Tabs if in Problem View */}
            <div className="h-10 shrink-0 px-5 bg-[#161f28] border-b border-[#2d3a4b] flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-slate-200 capitalize">
                  {activeRailTab}
                </span>
                {activeRailTab === 'problem' && (
                  <span className="text-[11px] text-slate-500">
                    Question {currentIndex + 1} of {variant.questions.length}
                  </span>
                )}
              </div>

              {markedForReview[currentQ.id] && (
                <span className="inline-flex items-center gap-1 text-[11px] text-amber-400 font-medium">
                  <Flag className="w-3 h-3 fill-current" />
                  Flagged
                </span>
              )}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-300 font-sans leading-relaxed text-sm">
              {activeRailTab === 'problem' && (
                <>
                  {/* Title & Metadata Row (HackerRank Style) */}
                  <div className="space-y-3 pb-3 border-b border-[#243342]">
                    <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                      {currentQ.title || currentQ.subtopic}
                    </h1>

                    <div className="flex flex-wrap items-center gap-3 text-xs">
                      <span className={`px-2.5 py-0.5 rounded font-semibold uppercase text-[11px] ${
                        currentQ.difficulty.toLowerCase() === 'hard'
                          ? 'bg-rose-950/80 text-rose-300 border border-rose-800/60'
                          : currentQ.difficulty.toLowerCase() === 'easy'
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                          : 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
                      }`}>
                        {currentQ.difficulty}
                      </span>

                      <span className="text-slate-400">
                        Max Score: <strong className="text-slate-200">15</strong>
                      </span>

                      <span className="text-slate-600">•</span>

                      <span className="text-slate-400">
                        Success Rate: <strong className="text-slate-200">92.4%</strong>
                      </span>

                      <span className="text-slate-600">•</span>

                      <span className="text-slate-400">
                        Domain: <span className="text-emerald-400">{currentQ.topic}</span>
                      </span>
                    </div>
                  </div>

                  {/* Problem Description & Formatted Blocks */}
                  <div className="space-y-4 text-slate-300 whitespace-pre-line leading-relaxed">
                    {baseDescription}
                  </div>

                  {/* Structured Examples (HackerRank Sample Cases) */}
                  {examples.length > 0 && (
                    <div className="space-y-4 pt-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Sample Input & Output:
                      </h3>

                      {examples.map((ex, i) => (
                        <div
                          key={i}
                          className="rounded-xl border border-[#2d3a4b] bg-[#161f28] p-4 space-y-3 shadow-sm font-mono text-xs"
                        >
                          <div className="text-xs font-bold text-emerald-400 font-sans">
                            {ex.title}:
                          </div>

                          {ex.input && (
                            <div className="space-y-1">
                              <div className="text-[11px] text-slate-400 font-sans uppercase font-bold">Input:</div>
                              <pre className="p-2.5 rounded bg-[#0d1117] border border-[#243342] text-amber-300 whitespace-pre-wrap break-all overflow-x-auto">
                                {ex.input}
                              </pre>
                            </div>
                          )}

                          {ex.output && (
                            <div className="space-y-1">
                              <div className="text-[11px] text-slate-400 font-sans uppercase font-bold">Output:</div>
                              <pre className="p-2.5 rounded bg-[#0d1117] border border-[#243342] text-emerald-400 whitespace-pre-wrap break-all overflow-x-auto">
                                {ex.output}
                              </pre>
                            </div>
                          )}

                          {ex.explanation && (
                            <div className="pt-2 border-t border-[#243342] text-slate-300 font-sans text-xs">
                              <strong className="text-slate-400">Explanation: </strong>
                              <span>{ex.explanation}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Constraints Section (HackerRank monospace pills) */}
                  {constraints.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Constraints:
                      </h3>
                      <div className="space-y-1.5 pl-1 font-mono text-xs">
                        {constraints.map((c, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                            <code className="px-2 py-0.5 rounded bg-[#161f28] border border-[#2d3a4b] text-indigo-300">
                              {c}
                            </code>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Algorithmic Hint */}
                  {currentQ.hint && (
                    <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-700/40 space-y-1.5">
                      <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
                        <Lightbulb className="w-4 h-4" />
                        <span>Algorithmic Hint</span>
                      </div>
                      <p className="text-xs text-amber-200/90 leading-relaxed font-sans">
                        {currentQ.hint}
                      </p>
                    </div>
                  )}
                </>
              )}

              {/* Submissions Tab View */}
              {activeRailTab === 'submissions' && (
                <div className="space-y-4">
                  <h2 className="text-base font-bold text-white">Your Run & Submission History</h2>
                  {submissionsHistory[currentQ.id]?.length ? (
                    <div className="space-y-2">
                      {submissionsHistory[currentQ.id].map((sub) => (
                        <div
                          key={sub.id}
                          className="p-3 rounded-xl border border-[#2d3a4b] bg-[#161f28] flex items-center justify-between text-xs font-mono"
                        >
                          <div className="flex items-center gap-2.5">
                            <span className={`w-2.5 h-2.5 rounded-full ${
                              sub.status === 'ACCEPTED' ? 'bg-emerald-400' : 'bg-rose-400'
                            }`} />
                            <span className="font-bold text-white uppercase">{sub.language}</span>
                            <span className="text-slate-400">({sub.timestamp})</span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className={sub.status === 'ACCEPTED' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                              {sub.passedCount} / {sub.totalCount} Test Cases
                            </span>
                            <span className="text-slate-400">{sub.runtimeMs} ms</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-500 border border-dashed border-[#2d3a4b] rounded-2xl text-xs">
                      No code runs yet for this challenge. Click &quot;Run Code&quot; to test your solution.
                    </div>
                  )}
                </div>
              )}

              {/* Leaderboard Tab View */}
              {activeRailTab === 'leaderboard' && (
                <div className="p-8 text-center text-slate-400 space-y-3">
                  <Award className="w-10 h-10 text-emerald-400 mx-auto" />
                  <h3 className="text-base font-bold text-white">Live OA Assessment Mode</h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    The competitive leaderboard will be published after the assessment window concludes and all test cases are graded.
                  </p>
                </div>
              )}

              {/* Discussions Tab View */}
              {activeRailTab === 'discussions' && (
                <div className="p-8 text-center text-slate-400 space-y-3">
                  <MessageSquare className="w-10 h-10 text-slate-500 mx-auto" />
                  <h3 className="text-base font-bold text-white">Discussions Disabled</h3>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    To maintain strict test integrity during proctored Online Assessments, community discussions are locked.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* ============================================================ */}
          {/* RIGHT AREA: Monaco Editor + HackerRank Bottom Actions & Console */}
          {/* ============================================================ */}
          <section className="h-full flex flex-col bg-[#0d1117] overflow-hidden">
            {!isCodingQuestion ? (
              /* Non-Coding (MCQ/MSQ) View */
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
                          ? 'bg-emerald-950/30 border-emerald-500 text-emerald-200 font-semibold shadow-sm'
                          : 'bg-[#161f28] border-[#2d3a4b] text-slate-300 hover:bg-[#212e3c]'
                      }`}
                    >
                      {opt}
                    </label>
                  );
                })}
              </div>
            ) : (
              /* Full Coding Question View */
              <>
                {/* Editor Header: Theme, Language, Reset, Format */}
                <div className="h-10 shrink-0 px-4 bg-[#161f28] border-b border-[#2d3a4b] flex items-center justify-between text-xs gap-3">
                  <div className="flex items-center gap-3">
                    {/* Theme Selector */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400 text-[11px]">Theme:</span>
                      <select
                        value={editorTheme}
                        onChange={(e) => setEditorTheme(e.target.value)}
                        className="bg-[#0d1117] border border-[#2d3a4b] hover:border-slate-500 rounded px-2 py-0.5 text-[11px] text-slate-200 focus:outline-none cursor-pointer"
                      >
                        {EDITOR_THEMES.map(t => (
                          <option key={t.id} value={t.id}>{t.label}</option>
                        ))}
                      </select>
                    </div>

                    {/* Language Selector */}
                    <div className="flex items-center gap-1.5">
                      <Code2 className="w-3.5 h-3.5 text-emerald-400" />
                      <select
                        value={currentLang}
                        onChange={(e) => handleLanguageChange(e.target.value)}
                        className="bg-[#0d1117] border border-[#2d3a4b] hover:border-slate-500 rounded px-2.5 py-0.5 text-[11px] font-semibold text-slate-200 focus:outline-none cursor-pointer"
                      >
                        {SUPPORTED_LANGUAGES.map(l => (
                          <option key={l.id} value={l.id}>{l.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Reset Code Button */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleResetCode}
                      className="flex items-center gap-1 text-slate-400 hover:text-white px-2 py-1 rounded hover:bg-[#212e3c] text-[11px] transition-colors"
                      title="Reset Boilerplate Code"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span className="hidden sm:inline">Reset</span>
                    </button>
                  </div>
                </div>

                {/* Monaco Editor Canvas */}
                <div className="flex-1 min-h-[220px] flex flex-col overflow-hidden relative">
                  <CodeEditor
                    value={currentCode}
                    onChange={handleCodeChange}
                    language={currentLang}
                    theme={editorTheme}
                    hideHeader={true}
                    showFooterStatus={false}
                    onCursorChange={(line, col) => setCursorPosition({ line, col })}
                    height="100%"
                  />
                </div>

                {/* ============================================================ */}
                {/* HACKERRANK BOTTOM FOOTER BAR */}
                {/* ============================================================ */}
                <div className="h-12 shrink-0 px-4 bg-[#161f28] border-t border-[#2d3a4b] flex items-center justify-between text-xs gap-3 select-none z-10">
                  {/* Left Side: Upload Code & Custom Input Checkbox */}
                  <div className="flex items-center gap-4">
                    {/* Upload Code as File */}
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      className="hidden"
                      accept=".cpp,.c,.java,.py,.js,.ts,.go,.rs,.cs,.sql,.txt"
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#212e3c] hover:bg-[#2c3d4f] text-slate-300 hover:text-white text-xs font-medium border border-slate-700/60 transition-colors"
                      title="Upload local code file"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Upload Code as File</span>
                    </button>

                    {/* Test against custom input checkbox */}
                    <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:text-white">
                      <input
                        type="checkbox"
                        checked={testAgainstCustomInput}
                        onChange={(e) => {
                          setTestAgainstCustomInput(e.target.checked);
                          if (e.target.checked) setIsConsoleExpanded(true);
                        }}
                        className="w-4 h-4 rounded bg-[#0d1117] border-slate-600 text-emerald-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                      />
                      <span>Test against custom input</span>
                    </label>
                  </div>

                  {/* Right Side: Line/Col Counter, Run Code, Submit Code */}
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
                      Line: {cursorPosition.line} Col: {cursorPosition.col}
                    </span>

                    {/* Run Code Button */}
                    <button
                      type="button"
                      onClick={handleRunCode}
                      disabled={isRunningCode}
                      className="px-4 py-1.5 rounded bg-[#212e3c] hover:bg-[#2c3d4f] text-white font-semibold flex items-center gap-1.5 border border-slate-600/80 transition-all text-xs disabled:opacity-50"
                    >
                      {isRunningCode ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-current text-slate-300" />
                          <span>Run Code</span>
                        </>
                      )}
                    </button>

                    {/* Submit Code Button (HackerRank Signature Green #1BA94C) */}
                    <button
                      type="button"
                      onClick={handleRunCode}
                      disabled={isRunningCode}
                      className="px-4 py-1.5 rounded bg-[#1BA94C] hover:bg-[#169642] text-white font-bold flex items-center gap-1.5 shadow-md shadow-emerald-700/20 transition-all text-xs disabled:opacity-50"
                    >
                      <span>Submit Code</span>
                    </button>
                  </div>
                </div>

                {/* ============================================================ */}
                {/* TEST CASES & RESULTS DRAWER (HACKERRANK STYLE) */}
                {/* ============================================================ */}
                <div
                  className={`flex flex-col border-t border-[#2d3a4b] bg-[#0d1117] transition-all duration-200 ${
                    isConsoleExpanded ? 'h-[270px]' : 'h-8'
                  }`}
                >
                  {/* Drawer Toggle Header */}
                  <div className="h-8 shrink-0 px-4 bg-[#161f28] border-b border-[#2d3a4b] flex items-center justify-between text-xs cursor-pointer"
                    onClick={() => setIsConsoleExpanded(!isConsoleExpanded)}
                  >
                    <div className="flex items-center gap-2">
                      <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="font-semibold text-slate-300">
                        {testAgainstCustomInput ? 'Custom Input Console' : 'Test Cases Output'}
                      </span>
                      {runResult && (
                        <span className={`px-2 py-0.2 rounded text-[10px] font-bold ${
                          runResult.status === 'ACCEPTED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
                        }`}>
                          {runResult.status}
                        </span>
                      )}
                    </div>

                    <button
                      type="button"
                      className="text-slate-400 hover:text-white p-0.5"
                    >
                      {isConsoleExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  {/* Drawer Content */}
                  {isConsoleExpanded && (
                    <div className="flex-1 overflow-y-auto p-4 text-xs font-mono">
                      {testAgainstCustomInput ? (
                        /* Custom Input Editor */
                        <div className="space-y-2 h-full flex flex-col">
                          <div className="text-[11px] text-slate-400 font-sans uppercase font-bold">
                            Enter Custom Input Data:
                          </div>
                          <textarea
                            value={customInputText}
                            onChange={(e) => setCustomInputText(e.target.value)}
                            placeholder="e.g. [[1,1,1,0,0,0],[0,1,0,0,0,0],[1,1,1,0,0,0],[0,0,2,4,4,0],[0,0,0,2,0,0],[0,0,1,2,4,0]]"
                            className="flex-1 w-full p-3 rounded-lg bg-[#161f28] border border-[#2d3a4b] text-slate-200 placeholder-slate-600 font-mono text-xs focus:outline-none focus:border-emerald-500 resize-none"
                          />
                        </div>
                      ) : (
                        /* Test Cases 0 to 14 View */
                        <div className="space-y-3">
                          {isRunningCode ? (
                            <div className="flex flex-col items-center justify-center py-10 text-slate-400 space-y-2">
                              <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
                              <span className="font-sans">Running solution across all test cases...</span>
                            </div>
                          ) : runResult ? (
                            <div className="space-y-3">
                              {/* Overall Status Banner */}
                              <div className="flex items-center justify-between pb-2 border-b border-[#243342]">
                                <div className="flex items-center gap-2">
                                  {runResult.status === 'ACCEPTED' ? (
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                  ) : (
                                    <AlertCircle className="w-4 h-4 text-rose-400" />
                                  )}
                                  <span className={`font-bold text-sm ${
                                    runResult.status === 'ACCEPTED' ? 'text-emerald-400' : 'text-rose-400'
                                  }`}>
                                    {runResult.status === 'ACCEPTED'
                                      ? 'Congratulations! You passed all test cases.'
                                      : runResult.status === 'WRONG_ANSWER'
                                      ? 'Wrong Answer: Output mismatch on some test cases.'
                                      : runResult.status === 'TLE'
                                      ? 'Time Limit Exceeded (TLE).'
                                      : 'Compilation or Runtime Error.'}
                                  </span>
                                </div>

                                <div className="flex items-center gap-3 text-slate-400 text-xs">
                                  <span>Runtime: <strong className="text-white">{runResult.runtime_ms} ms</strong></span>
                                  <span>Memory: <strong className="text-white">{runResult.memory_mb} MB</strong></span>
                                </div>
                              </div>

                              {/* Compiler stderr if any */}
                              {runResult.compiler_output && runResult.status !== 'ACCEPTED' && (
                                <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-800/50 text-rose-300 whitespace-pre-wrap">
                                  {runResult.compiler_output}
                                </div>
                              )}

                              {/* Test Case Pills: Test Case 0, Test Case 1, etc. */}
                              {runResult.test_case_results?.length > 0 && (
                                <>
                                  <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-[#243342] scrollbar-none">
                                    {runResult.test_case_results.map((tc, idx) => (
                                      <button
                                        key={idx}
                                        type="button"
                                        onClick={() => setSelectedCaseIdx(idx)}
                                        className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition-all ${
                                          selectedCaseIdx === idx
                                            ? 'bg-[#212e3c] text-white border border-slate-500 font-bold'
                                            : 'text-slate-400 hover:text-white bg-[#161f28]'
                                        }`}
                                      >
                                        <span className={`w-2 h-2 rounded-full ${tc.passed ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                                        <span>Test Case {idx}</span>
                                      </button>
                                    ))}
                                  </div>

                                  {/* Detailed View of Selected Test Case */}
                                  {runResult.test_case_results[selectedCaseIdx] && (
                                    <div className="space-y-2 pt-1">
                                      <div className="space-y-1">
                                        <span className="text-[11px] text-slate-400 font-sans uppercase font-bold">Compiler Message:</span>
                                        <div className={`p-2 rounded bg-[#161f28] border ${
                                          runResult.test_case_results[selectedCaseIdx].passed
                                            ? 'border-emerald-800/60 text-emerald-400'
                                            : 'border-rose-800/60 text-rose-400'
                                        }`}>
                                          {runResult.test_case_results[selectedCaseIdx].passed ? 'Success' : 'Wrong Answer'}
                                        </div>
                                      </div>

                                      <div className="space-y-1">
                                        <span className="text-[11px] text-slate-400 font-sans uppercase font-bold">Input:</span>
                                        <div className="p-2.5 rounded bg-[#161f28] border border-[#243342] text-amber-300 break-all overflow-x-auto">
                                          {runResult.test_case_results[selectedCaseIdx].input_data}
                                        </div>
                                      </div>

                                      <div className="space-y-1">
                                        <span className="text-[11px] text-slate-400 font-sans uppercase font-bold">Your Output:</span>
                                        <div className={`p-2.5 rounded border break-all ${
                                          runResult.test_case_results[selectedCaseIdx].passed
                                            ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-400'
                                            : 'bg-rose-950/20 border-rose-800/60 text-rose-400'
                                        }`}>
                                          {runResult.test_case_results[selectedCaseIdx].actual_output}
                                        </div>
                                      </div>

                                      <div className="space-y-1">
                                        <span className="text-[11px] text-slate-400 font-sans uppercase font-bold">Expected Output:</span>
                                        <div className="p-2.5 rounded bg-[#161f28] border border-[#243342] text-emerald-400 break-all">
                                          {runResult.test_case_results[selectedCaseIdx].expected_output}
                                        </div>
                                      </div>
                                    </div>
                                  )}
                                </>
                              )}
                            </div>
                          ) : (
                            /* Initial test case preview when not run yet */
                            <div className="space-y-3">
                              <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-[#243342]">
                                {sampleCases.map((_, idx) => (
                                  <button
                                    key={idx}
                                    type="button"
                                    onClick={() => setSelectedCaseIdx(idx)}
                                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                                      selectedCaseIdx === idx
                                        ? 'bg-[#212e3c] text-white border border-slate-500 font-bold'
                                        : 'text-slate-400 hover:text-white bg-[#161f28]'
                                    }`}
                                  >
                                    Test Case {idx}
                                  </button>
                                ))}
                              </div>

                              {sampleCases[selectedCaseIdx] && (
                                <div className="space-y-2 pt-1">
                                  <div className="space-y-1">
                                    <span className="text-[11px] text-slate-400 font-sans uppercase font-bold">Input:</span>
                                    <pre className="p-2.5 rounded bg-[#161f28] border border-[#243342] text-amber-300 break-all overflow-x-auto">
                                      {typeof sampleCases[selectedCaseIdx].input === 'object'
                                        ? JSON.stringify(sampleCases[selectedCaseIdx].input)
                                        : String(sampleCases[selectedCaseIdx].input)}
                                    </pre>
                                  </div>

                                  <div className="space-y-1">
                                    <span className="text-[11px] text-slate-400 font-sans uppercase font-bold">Expected Output:</span>
                                    <pre className="p-2.5 rounded bg-[#161f28] border border-[#243342] text-emerald-400 break-all">
                                      {String(sampleCases[selectedCaseIdx].expected_output)}
                                    </pre>
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
              </>
            )}
          </section>
        </div>
      </div>

      {/* Confirmation Modal for Exam Submission */}
      {showConfirmSubmit && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-2xl bg-[#161f28] border border-[#2d3a4b] shadow-2xl space-y-5">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Submit Online Assessment?</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              You have answered <strong className="text-white">{answeredCount}</strong> out of{' '}
              <strong className="text-white">{variant.questions.length}</strong> questions.
              Once submitted, all coding challenges will be thoroughly evaluated across standard and hidden test cases.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmSubmit(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#212e3c] text-slate-300 hover:bg-[#2c3d4f] transition-colors"
              >
                Continue Assessment
              </button>

              <button
                type="button"
                onClick={handleSubmitExam}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-[#1BA94C] hover:bg-[#169642] text-white flex items-center gap-1.5 shadow-lg shadow-emerald-700/25 transition-all disabled:opacity-50"
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
