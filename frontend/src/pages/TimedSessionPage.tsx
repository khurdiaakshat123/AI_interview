import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Clock, ShieldAlert, CheckCircle2, XCircle, AlertCircle, 
  HelpCircle, Sparkles, BookOpen, Code2, ArrowLeft, ArrowRight, 
  Share2, Copy, Check, Maximize2, Minimize2, Play, RotateCcw, 
  Layers, CheckSquare, Award, FileText, ChevronRight, ChevronLeft,
  X, ExternalLink, Flag, Send
} from 'lucide-react';
import confetti from 'canvas-confetti';
import Editor, { OnMount } from '@monaco-editor/react';
import { api } from '../services/api';
import { 
  CustomPracticeSessionData, 
  CustomSessionQuestion, 
  CustomSessionResult 
} from '../types';
import { TimedPracticeConfigModal } from '../components/practice/TimedPracticeConfigModal';
import { MCQCodeBlock } from '../components/mcq/MCQCodeBlock';

const DSA_LANGUAGES = [
  { id: 'cpp', label: 'C++ 20', monacoLang: 'cpp' },
  { id: 'python3', label: 'Python 3', monacoLang: 'python' },
  { id: 'java', label: 'Java 17', monacoLang: 'java' },
  { id: 'javascript', label: 'JavaScript', monacoLang: 'javascript' },
  { id: 'typescript', label: 'TypeScript', monacoLang: 'typescript' }
];

export const TimedSessionPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();

  // Lifecycle stage: 'loading' | 'briefing' | 'running' | 'summary' | 'config'
  const [stage, setStage] = useState<'loading' | 'briefing' | 'running' | 'summary' | 'config'>(
    sessionId ? 'loading' : 'config'
  );

  // Session Data
  const [session, setSession] = useState<CustomPracticeSessionData | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);

  // Briefing Stage State
  const [acknowledged, setAcknowledged] = useState<boolean>(false);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);

  // Running Test State
  const [activeSectionId, setActiveSectionId] = useState<string>('');
  const [activeQuestionIndex, setActiveQuestionIndex] = useState<number>(0);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, string>>({});
  const [markedForReview, setMarkedForReview] = useState<Record<string, boolean>>({});
  const [codingCodes, setCodingCodes] = useState<Record<string, { code: string; language: string }>>({});
  const [codingResults, setCodingResults] = useState<Record<string, any>>({});
  const [runningCodeId, setRunningCodeId] = useState<string | null>(null);
  const [consoleOutput, setConsoleOutput] = useState<any>(null);

  // Timer State
  const [timeRemaining, setTimeRemaining] = useState<number>(1800); // in seconds
  const [timeSpent, setTimeSpent] = useState<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fullscreen & Exit Security State
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [fullscreenWarning, setFullscreenWarning] = useState<boolean>(false);
  const [confirmSubmitModal, setConfirmSubmitModal] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Final Summary / Report State
  const [sessionResult, setSessionResult] = useState<CustomSessionResult | null>(null);
  const [reviewFilter, setReviewFilter] = useState<'all' | 'incorrect' | 'correct' | 'unattempted'>('all');

  // Config modal fallback state if no sessionId in URL
  const [configModalOpen, setConfigModalOpen] = useState<boolean>(!sessionId);

  // Monaco Editor Ref
  const editorRef = useRef<any>(null);

  // Load Session by ID
  useEffect(() => {
    if (!sessionId) {
      setStage('config');
      setConfigModalOpen(true);
      return;
    }

    setStage('loading');
    api.getCustomSession(sessionId)
      .then(res => {
        setSession(res);
        setTimeRemaining(res.duration_minutes * 60);
        if (res.sections && res.sections.length > 0) {
          setActiveSectionId(res.sections[0].id);
        }
        // Initialize starter code for DSA questions
        const initialCodes: Record<string, { code: string; language: string }> = {};
        res.questions.forEach(q => {
          if (q.type === 'dsa') {
            const starter = q.starterCode?.cpp || q.starterCode?.python3 || '// Write your solution here\n';
            initialCodes[q.id] = { code: starter, language: 'cpp' };
          }
        });
        setCodingCodes(initialCodes);
        setStage('briefing');
      })
      .catch(err => {
        console.error('Failed to load session:', err);
        setLoadingError(err.message || 'Failed to load practice session.');
        setStage('loading');
      });
  }, [sessionId]);

  // Fullscreen monitor
  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement);
      setIsFullscreen(active);
      if (!active && stage === 'running') {
        setFullscreenWarning(true);
      } else {
        setFullscreenWarning(false);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, [stage]);

  // BeforeUnload Exit Lock
  useEffect(() => {
    if (stage !== 'running') return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = 'Assessment in progress! Are you sure you want to leave? Your progress will not be saved.';
      return e.returnValue;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [stage]);

  // Countdown Timer Hook
  useEffect(() => {
    if (stage !== 'running') {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setTimeSpent(prev => prev + 1);
      setTimeRemaining(prev => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          handleFinalSubmit(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [stage]);

  // Request Fullscreen Helper
  const requestAppFullscreen = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } catch (err) {
      console.warn('Fullscreen request blocked or ignored:', err);
    }
  };

  // Exit Fullscreen Helper
  const exitAppFullscreen = async () => {
    try {
      if (document.fullscreenElement && document.exitFullscreen) {
        await document.exitFullscreen();
      }
    } catch {}
  };

  // Start Assessment
  const handleStartSession = async () => {
    if (!acknowledged) return;
    await requestAppFullscreen();
    setStage('running');
  };

  // Copy share URL
  const handleCopyLink = () => {
    const url = window.location.href;
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  // Active Questions for current section
  const currentSectionQuestions = session?.questions.filter(
    q => q.section_id === activeSectionId
  ) || [];

  const activeQuestion = currentSectionQuestions[activeQuestionIndex] || null;

  // Question navigation
  const handleSelectQuestion = (sectionId: string, qIdx: number) => {
    setActiveSectionId(sectionId);
    setActiveQuestionIndex(qIdx);
    setConsoleOutput(null);
  };

  const handleNextQuestion = () => {
    if (activeQuestionIndex < currentSectionQuestions.length - 1) {
      setActiveQuestionIndex(prev => prev + 1);
      setConsoleOutput(null);
    } else {
      // Advance to next section if available
      const currentSecIdx = session?.sections.findIndex(s => s.id === activeSectionId) ?? -1;
      if (session && currentSecIdx !== -1 && currentSecIdx < session.sections.length - 1) {
        setActiveSectionId(session.sections[currentSecIdx + 1].id);
        setActiveQuestionIndex(0);
        setConsoleOutput(null);
      }
    }
  };

  const handlePrevQuestion = () => {
    if (activeQuestionIndex > 0) {
      setActiveQuestionIndex(prev => prev - 1);
      setConsoleOutput(null);
    } else {
      // Go back to previous section if available
      const currentSecIdx = session?.sections.findIndex(s => s.id === activeSectionId) ?? -1;
      if (session && currentSecIdx > 0) {
        const prevSecId = session.sections[currentSecIdx - 1].id;
        const prevSecQs = session.questions.filter(q => q.section_id === prevSecId);
        setActiveSectionId(prevSecId);
        setActiveQuestionIndex(Math.max(0, prevSecQs.length - 1));
        setConsoleOutput(null);
      }
    }
  };

  // Select MCQ Option
  const handleSelectMcqOption = (qid: string, optionKey: string) => {
    setMcqAnswers(prev => ({
      ...prev,
      [qid]: optionKey
    }));
  };

  const handleClearMcqResponse = (qid: string) => {
    setMcqAnswers(prev => {
      const copy = { ...prev };
      delete copy[qid];
      return copy;
    });
  };

  const toggleMarkForReview = (qid: string) => {
    setMarkedForReview(prev => ({
      ...prev,
      [qid]: !prev[qid]
    }));
  };

  // DSA Code Run against Sample Test Cases
  const handleRunDsaCode = async (q: CustomSessionQuestion) => {
    if (!q || q.type !== 'dsa') return;
    const currentCode = codingCodes[q.id]?.code || '';
    const currentLang = codingCodes[q.id]?.language || 'cpp';

    setRunningCodeId(q.id);
    setConsoleOutput({ status: 'running', message: 'Executing solution against sample testcases...' });

    try {
      const res = await api.runLCCode(q.slug || q.id, currentCode, currentLang);
      const passed = res.passed_test_cases ?? (res.is_correct ? 1 : 0);
      const total = res.total_test_cases ?? 1;
      setConsoleOutput({
        status: res.status,
        passed,
        total,
        error: res.feedback || (res.status !== 'Accepted' ? res.status : undefined),
        runtime_ms: res.runtime_ms,
        memory_mb: res.memory_mb,
        test_results: res.test_case_results
      });
      setCodingResults(prev => ({
        ...prev,
        [q.id]: {
          status: res.status,
          passed_tests: passed,
          total_tests: total,
          code: currentCode,
          language: currentLang
        }
      }));
    } catch (err: any) {
      setConsoleOutput({
        status: 'Runtime Error',
        error: err.message || 'Execution failed'
      });
    } finally {
      setRunningCodeId(null);
    }
  };

  // Submit Assessment Final
  const handleFinalSubmit = async (isAutoSubmit: boolean = false) => {
    if (!session || !sessionId) return;
    setIsSubmitting(true);

    try {
      if (timerRef.current) clearInterval(timerRef.current);

      const payload = {
        mcq_answers: mcqAnswers,
        coding_submissions: codingResults,
        time_spent_seconds: timeSpent
      };

      const result = await api.submitCustomSession(sessionId, payload);
      setSessionResult(result);
      setConfirmSubmitModal(false);
      setStage('summary');
      await exitAppFullscreen();

      // Trigger celebratory confetti
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 }
      });
    } catch (err: any) {
      console.error('Failed to submit session:', err);
      alert('Failed to submit assessment: ' + (err.message || 'Unknown error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper formatting for seconds to MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Palette Status Helper
  const getQuestionStatus = (q: CustomSessionQuestion) => {
    const isMarked = markedForReview[q.id];
    let isAnswered = false;

    if (q.type === 'mcq') {
      isAnswered = Boolean(mcqAnswers[q.id]);
    } else {
      isAnswered = Boolean(codingResults[q.id] || (codingCodes[q.id]?.code && codingCodes[q.id].code.trim().length > 30));
    }

    if (isMarked && isAnswered) return 'marked-answered';
    if (isMarked) return 'marked';
    if (isAnswered) return 'answered';
    return 'unanswered';
  };

  // =========================================================================
  // RENDER: LOADING STATE
  // =========================================================================
  if (stage === 'loading') {
    return (
      <div className="min-h-screen bg-bg text-text flex flex-col items-center justify-center p-6 space-y-4">
        {loadingError ? (
          <div className="max-w-md w-full p-6 rounded-2xl bg-surface border border-rose-500/30 text-center space-y-4 shadow-xl">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-text">Practice Session Not Found</h2>
            <p className="text-xs text-text-muted">{loadingError}</p>
            <button
              type="button"
              onClick={() => navigate('/practice')}
              className="px-4 py-2 rounded-xl bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors"
            >
              Back to Practice Hub
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-3 border-accent/20 border-t-accent rounded-full animate-spin" />
            <span className="text-xs font-mono text-text-muted">Loading Practice Assessment...</span>
          </div>
        )}
      </div>
    );
  }

  // =========================================================================
  // RENDER: BRIEFING & INSTRUCTIONS STAGE
  // =========================================================================
  if (stage === 'briefing' && session) {
    const mcqCount = session.questions.filter(q => q.type === 'mcq').length;
    const dsaCount = session.questions.filter(q => q.type === 'dsa').length;

    return (
      <div className="min-h-screen bg-bg text-text flex flex-col">
        {/* Top Navbar */}
        <header className="h-16 bg-surface border-b border-border px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/practice')}
              className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text hover:bg-surface-hover transition-colors"
              title="Return to Practice"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <span className="font-serif text-lg font-bold text-text">intervyn</span>
              <span className="text-border">/</span>
              <span className="text-xs font-mono font-medium text-accent">Timed Assessment Briefing</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleCopyLink}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg text-text-muted hover:text-text hover:border-accent text-xs font-medium transition-colors"
          >
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
            <span>{copiedLink ? 'Share Link Copied!' : 'Share Practice Link'}</span>
          </button>
        </header>

        {/* Briefing Content Container */}
        <div className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-8 space-y-6">
          
          {/* Header Card */}
          <div className="p-6 rounded-2xl bg-surface border border-border shadow-sm space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold uppercase tracking-wider ${
                session.session_type === 'hybrid'
                  ? 'bg-purple-500/10 text-purple-500 border border-purple-500/20'
                  : session.session_type === 'mcq'
                  ? 'bg-blue-500/10 text-blue-500 border border-blue-500/20'
                  : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
              }`}>
                {session.session_type === 'hybrid' ? 'MCQ & DSA' : session.session_type.toUpperCase()} ASSESSMENT
              </span>

              <div className="flex items-center gap-4 text-xs font-mono text-text-muted">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-accent" />
                  <strong>{session.duration_minutes} Minutes Allowed</strong>
                </span>
                <span className="text-border">|</span>
                <span><strong>{session.total_questions} Total Questions</strong></span>
              </div>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold font-serif text-text tracking-tight">
              {session.title}
            </h1>
            <p className="text-xs text-text-muted leading-relaxed">
              This timed practice session has been prepared and calibrated according to your selected topic and difficulty specifications. Read the format rules below before starting.
            </p>
          </div>

          {/* Marking Format Breakdown Alert (CRITICAL USER REQUIREMENT) */}
          <div className="p-5 rounded-2xl bg-surface border border-accent/30 space-y-3 shadow-xs">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                <Award className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-text">Negative Marking & Evaluation Format</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-bg border border-border space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-text flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-blue-500" />
                    Multiple Choice Questions
                  </span>
                  <span className="font-mono text-xs font-bold text-blue-500">{mcqCount} Qs</span>
                </div>
                <div className="space-y-1 font-mono text-[11px] text-text-muted">
                  <div className="flex justify-between">
                    <span>Correct Answer:</span>
                    <strong className="text-emerald-500">+{session.marking_scheme.mcq_correct.toFixed(2)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Incorrect Answer (Penalty):</span>
                    <strong className="text-rose-500">{session.marking_scheme.mcq_negative.toFixed(2)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Unattempted / Skipped:</span>
                    <span className="text-text-muted">0.00</span>
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-bg border border-border space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-text flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5 text-amber-500" />
                    DSA & Coding Problems
                  </span>
                  <span className="font-mono text-xs font-bold text-amber-500">{dsaCount} Qs</span>
                </div>
                <div className="space-y-1 font-mono text-[11px] text-text-muted">
                  <div className="flex justify-between">
                    <span>Automated Evaluation:</span>
                    <strong className="text-accent">{session.marking_scheme.coding_weight.toFixed(1)} Pts / Problem</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Partial Testcase Credit:</span>
                    <span className="text-text">Enabled</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Supported Languages:</span>
                    <span className="text-text">C++, Python, Java, JS</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Sections Overview */}
          <div className="p-5 rounded-2xl bg-surface border border-border space-y-3">
            <h3 className="text-sm font-bold text-text flex items-center gap-2">
              <Layers className="w-4 h-4 text-text-muted" />
              <span>Section Breakdown ({session.sections.length} Sections)</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {session.sections.map((s, idx) => (
                <div key={s.id} className="p-3.5 rounded-xl bg-bg border border-border space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-text font-mono">
                      {idx + 1}. {s.name}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider bg-surface border border-border text-text-muted">
                      {s.section_type.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[11px] text-text-muted font-mono flex items-center gap-3">
                    <span>Topic: <strong className="text-text">{s.topic}</strong></span>
                    <span>Diff: <strong className="text-text">{s.difficulty}</strong></span>
                    <span>Count: <strong className="text-text">{s.count}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Test Guidelines & Anti-Cheat Rules */}
          <div className="p-5 rounded-2xl bg-surface border border-border space-y-2 text-xs">
            <h3 className="font-bold text-text flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-500" />
              <span>Assessment Guidelines & Conduct</span>
            </h3>
            <ul className="list-disc list-inside space-y-1.5 text-text-muted leading-relaxed">
              <li>The assessment enters <strong className="text-text">Full-Screen Mode</strong> as soon as you click Start.</li>
              <li>Exiting full-screen or switching tabs triggers an active security warning overlay.</li>
              <li>You <strong className="text-text">cannot navigate back</strong> or reload the page without submitting your responses.</li>
              <li>The countdown timer runs continuously in the background and will <strong className="text-text">automatically submit</strong> when time expires.</li>
            </ul>
          </div>

          {/* Candidate Acknowledgement Checkbox */}
          <div className="p-4 rounded-xl bg-accent/5 border border-accent/20 flex items-start gap-3">
            <input
              type="checkbox"
              id="acknowledge"
              checked={acknowledged}
              onChange={e => setAcknowledged(e.target.checked)}
              className="mt-0.5 w-4 h-4 rounded text-accent focus:ring-0 cursor-pointer"
            />
            <label htmlFor="acknowledge" className="text-xs text-text cursor-pointer select-none leading-relaxed">
              <strong>I acknowledge and agree:</strong> I have read all test instructions and negative marking rules (+1.00 for correct, -0.25 for incorrect). I understand that once I click Start, the assessment will lock into full-screen mode and I cannot leave without submitting.
            </label>
          </div>

          {/* Start Test Button */}
          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={handleStartSession}
              disabled={!acknowledged}
              className="flex items-center gap-2.5 px-8 py-3 rounded-xl bg-accent text-accent-contrast text-sm font-semibold hover:bg-accent-hover transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-lg hover:shadow-xl"
            >
              <Maximize2 className="w-4 h-4" />
              <span>Start Practice Session</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </div>
      </div>
    );
  }

  // =========================================================================
  // RENDER: RUNNING FULLSCREEN ASSESSMENT
  // =========================================================================
  if (stage === 'running' && session) {
    const isWarningTimer = timeRemaining <= 300;
    const isDangerTimer = timeRemaining <= 60;

    return (
      <div className="h-screen w-screen bg-bg text-text flex flex-col overflow-hidden select-none">
        
        {/* Fullscreen Warning Overlay */}
        {fullscreenWarning && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="max-w-md w-full p-6 rounded-2xl bg-surface border border-amber-500/40 text-center space-y-4 shadow-2xl">
              <div className="w-12 h-12 rounded-full bg-amber-500/10 text-amber-500 flex items-center justify-center mx-auto">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-text">Security Warning: Full-Screen Exited</h3>
              <p className="text-xs text-text-muted leading-relaxed">
                You have exited full-screen mode. In accordance with test integrity guidelines, please return to full-screen mode immediately to continue your assessment.
              </p>
              <button
                type="button"
                onClick={() => {
                  requestAppFullscreen();
                  setFullscreenWarning(false);
                }}
                className="w-full py-2.5 rounded-xl bg-accent text-accent-contrast text-xs font-semibold hover:bg-accent-hover transition-colors"
              >
                Return to Full-Screen Mode
              </button>
            </div>
          </div>
        )}

        {/* Top Assessment Header */}
        <header className="h-14 bg-surface border-b border-border px-4 sm:px-6 flex items-center justify-between shrink-0 z-30">
          {/* Left: Brand Mark, Test Title & Section Tabs */}
          <div className="flex items-center gap-3 overflow-x-auto">
            <div className="flex items-center gap-1.5 shrink-0 select-none">
              <span className="font-serif text-base font-semibold text-text tracking-tight">
                intervyn<span className="text-accent">.</span>
              </span>
            </div>
            <span className="text-border">|</span>
            <span className="font-serif text-xs font-semibold text-text truncate max-w-xs hidden md:inline">
              {session.title}
            </span>
            <div className="flex items-center gap-1.5 p-1 bg-bg rounded-lg border border-border">
              {session.sections.map((sec, idx) => (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => {
                    setActiveSectionId(sec.id);
                    setActiveQuestionIndex(0);
                    setConsoleOutput(null);
                  }}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    activeSectionId === sec.id
                      ? 'bg-surface text-text shadow-xs font-semibold'
                      : 'text-text-muted hover:text-text'
                  }`}
                >
                  {sec.name}
                </button>
              ))}
            </div>
          </div>

          {/* Right: Live Countdown Timer & Submit Action */}
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-mono text-xs font-bold transition-all ${
              isDangerTimer
                ? 'bg-rose-500/15 text-rose-500 border-rose-500/40 animate-pulse'
                : isWarningTimer
                ? 'bg-amber-500/15 text-amber-500 border-amber-500/40'
                : 'bg-bg text-text border-border'
            }`}>
              <Clock className="w-3.5 h-3.5" />
              <span>{formatTime(timeRemaining)}</span>
            </div>

            <button
              type="button"
              onClick={() => setConfirmSubmitModal(true)}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors shadow-sm"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Submit Assessment</span>
            </button>
          </div>
        </header>

        {/* Main Workspace (Split: Question / Code on Left/Center, Palette on Right) */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          
          {/* Main Question Execution Canvas */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            
            {activeQuestion ? (
              activeQuestion.type === 'mcq' ? (
                // ===================================
                // MCQ QUESTION INTERFACE
                // ===================================
                <div className="flex-1 flex flex-col min-h-0 overflow-y-auto p-6 sm:p-8 space-y-6">
                  
                  {/* Question Header Status */}
                  <div className="flex items-center justify-between border-b border-border pb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-accent">
                        Question {activeQuestionIndex + 1} of {currentSectionQuestions.length}
                      </span>
                      <span className="text-border">|</span>
                      <span className="text-xs text-text-muted font-mono">{activeQuestion.broad_topic_name || activeQuestion.subcategory || "General"}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider ${
                        activeQuestion.difficulty === 'Easy'
                          ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                          : activeQuestion.difficulty === 'Medium'
                          ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                      }`}>
                        {activeQuestion.difficulty}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-bg border border-border text-[11px] font-mono text-text-muted">
                        Marking: <strong className="text-emerald-500">+{session.marking_scheme.mcq_correct.toFixed(2)}</strong> / <strong className="text-rose-500">{session.marking_scheme.mcq_negative.toFixed(2)}</strong>
                      </span>
                    </div>
                  </div>

                  {/* Question Text */}
                  <div className="text-sm sm:text-base font-medium text-text leading-relaxed whitespace-pre-wrap">
                    {activeQuestion.question}
                  </div>

                  {/* Optional Code Snippet */}
                  {activeQuestion.has_code && activeQuestion.code_snippet && (
                    <MCQCodeBlock code={activeQuestion.code_snippet} />
                  )}

                  {/* Options (A, B, C, D) */}
                  <div className="space-y-3 pt-2">
                    {Object.entries(activeQuestion.options || {}).map(([optKey, optText]) => {
                      const isSelected = mcqAnswers[activeQuestion.id] === optKey;
                      return (
                        <div
                          key={optKey}
                          onClick={() => handleSelectMcqOption(activeQuestion.id, optKey)}
                          className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3 select-none ${
                            isSelected
                              ? 'bg-accent/15 border-accent text-text shadow-sm'
                              : 'bg-surface border-border hover:border-border-focus hover:bg-surface-hover text-text'
                          }`}
                        >
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center font-mono text-xs font-bold shrink-0 mt-0.5 ${
                            isSelected
                              ? 'bg-accent text-accent-contrast'
                              : 'bg-bg border border-border text-text-muted'
                          }`}>
                            {optKey}
                          </div>
                          <div className="text-xs sm:text-sm leading-relaxed flex-1 pt-0.5 font-sans">
                            {optText}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Action Bar */}
                  <div className="pt-6 border-t border-border flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => toggleMarkForReview(activeQuestion.id)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          markedForReview[activeQuestion.id]
                            ? 'bg-purple-500/15 text-purple-400 border-purple-500/40'
                            : 'bg-surface text-text-muted border-border hover:text-text'
                        }`}
                      >
                        <Flag className="w-3.5 h-3.5" />
                        <span>{markedForReview[activeQuestion.id] ? 'Marked for Review' : 'Mark for Review'}</span>
                      </button>

                      {mcqAnswers[activeQuestion.id] && (
                        <button
                          type="button"
                          onClick={() => handleClearMcqResponse(activeQuestion.id)}
                          className="px-3 py-1.5 rounded-lg text-xs font-medium text-text-muted hover:text-rose-500 hover:bg-surface transition-colors"
                        >
                          Clear Response
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handlePrevQuestion}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-text hover:bg-surface-hover transition-colors"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                        <span>Previous</span>
                      </button>

                      <button
                        type="button"
                        onClick={handleNextQuestion}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors"
                      >
                        <span>Next</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                </div>
              ) : (
                // ===================================
                // DSA CODING INTERFACE
                // ===================================
                <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
                  
                  {/* Left: Problem Description */}
                  <div className="w-full lg:w-1/2 flex flex-col bg-bg border-b lg:border-b-0 lg:border-r border-border min-h-0 overflow-y-auto p-5 sm:p-6 space-y-4">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-accent">Problem {activeQuestionIndex + 1}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider ${
                            activeQuestion.difficulty === 'Easy'
                              ? 'bg-emerald-500/10 text-emerald-500'
                              : activeQuestion.difficulty === 'Medium'
                              ? 'bg-amber-500/10 text-amber-500'
                              : 'bg-rose-500/10 text-rose-500'
                          }`}>
                            {activeQuestion.difficulty}
                          </span>
                        </div>
                        <h2 className="text-lg font-bold text-text mt-1">{activeQuestion.title}</h2>
                      </div>
                      <span className="text-xs font-mono text-accent">10.0 Pts</span>
                    </div>

                    <div 
                      className="text-xs text-text leading-relaxed prose prose-invert max-w-none space-y-3"
                      dangerouslySetInnerHTML={{ __html: activeQuestion.contentHtml || activeQuestion.contentMarkdown || 'Problem description loading...' }}
                    />

                    {/* Sample Test Cases */}
                    {activeQuestion.sampleTestCases && activeQuestion.sampleTestCases.length > 0 && (
                      <div className="space-y-3 pt-2">
                        <span className="text-xs font-bold text-text uppercase font-mono tracking-wider">Example Test Cases</span>
                        {activeQuestion.sampleTestCases.map((tc, tcIdx) => (
                          <div key={tcIdx} className="p-3 rounded-lg bg-surface border border-border font-mono text-xs space-y-1">
                            <div><strong className="text-text-muted">Input:</strong> <span className="text-text">{tc.input}</span></div>
                            <div><strong className="text-text-muted">Expected:</strong> <span className="text-emerald-400">{tc.output}</span></div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right: Monaco Code Editor & Live Runner */}
                  <div className="w-full lg:w-1/2 flex flex-col bg-surface min-h-0 overflow-hidden">
                    
                    {/* Editor Header */}
                    <div className="h-10 px-4 border-b border-border bg-surface flex items-center justify-between shrink-0">
                      <div className="flex items-center gap-2">
                        <select
                          value={codingCodes[activeQuestion.id]?.language || 'cpp'}
                          onChange={e => {
                            const newLang = e.target.value;
                            const starter = activeQuestion.starterCode?.[newLang] || '// Solution\n';
                            setCodingCodes(prev => ({
                              ...prev,
                              [activeQuestion.id]: { code: starter, language: newLang }
                            }));
                          }}
                          className="px-2 py-1 rounded bg-bg border border-border text-xs font-mono text-text cursor-pointer"
                        >
                          {DSA_LANGUAGES.map(l => (
                            <option key={l.id} value={l.id}>{l.label}</option>
                          ))}
                        </select>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleRunDsaCode(activeQuestion)}
                          disabled={runningCodeId === activeQuestion.id}
                          className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors cursor-pointer"
                        >
                          {runningCodeId === activeQuestion.id ? (
                            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          ) : (
                            <Play className="w-3 h-3 fill-current" />
                          )}
                          <span>Run Code</span>
                        </button>
                      </div>
                    </div>

                    {/* Monaco Editor Canvas */}
                    <div className="flex-1 w-full min-h-0 relative">
                      <Editor
                        height="100%"
                        language={DSA_LANGUAGES.find(l => l.id === (codingCodes[activeQuestion.id]?.language || 'cpp'))?.monacoLang || 'cpp'}
                        theme="vs-dark"
                        value={codingCodes[activeQuestion.id]?.code || ''}
                        onChange={val => {
                          const curLang = codingCodes[activeQuestion.id]?.language || 'cpp';
                          setCodingCodes(prev => ({
                            ...prev,
                            [activeQuestion.id]: { code: val || '', language: curLang }
                          }));
                        }}
                        options={{
                          fontSize: 13,
                          fontFamily: '"JetBrains Mono", Consolas, monospace',
                          minimap: { enabled: false },
                          automaticLayout: true,
                          scrollBeyondLastLine: false,
                          tabSize: 4
                        }}
                      />
                    </div>

                    {/* Console Output Drawer */}
                    {consoleOutput && (
                      <div className="h-44 border-t border-border bg-bg flex flex-col shrink-0">
                        <div className="h-8 px-3 border-b border-border bg-surface flex items-center justify-between">
                          <span className="text-xs font-mono font-semibold text-text">Test Output</span>
                          <button
                            type="button"
                            onClick={() => setConsoleOutput(null)}
                            className="text-text-muted hover:text-text p-1"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="flex-1 p-3 overflow-y-auto font-mono text-xs space-y-2">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded font-bold ${
                              consoleOutput.status === 'Accepted'
                                ? 'bg-emerald-500/10 text-emerald-500'
                                : 'bg-rose-500/10 text-rose-500'
                            }`}>
                              {consoleOutput.status}
                            </span>
                            {consoleOutput.passed !== undefined && (
                              <span className="text-text-muted">Passed: {consoleOutput.passed} / {consoleOutput.total}</span>
                            )}
                            {consoleOutput.runtime_ms && (
                              <span className="text-text-muted">Runtime: {consoleOutput.runtime_ms} ms</span>
                            )}
                          </div>
                          {consoleOutput.error && (
                            <pre className="text-rose-400 whitespace-pre-wrap">{consoleOutput.error}</pre>
                          )}
                          {consoleOutput.stdout && (
                            <pre className="text-text whitespace-pre-wrap">{consoleOutput.stdout}</pre>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Bottom Navigation */}
                    <div className="h-12 px-4 border-t border-border bg-surface flex items-center justify-between shrink-0">
                      <button
                        type="button"
                        onClick={() => toggleMarkForReview(activeQuestion.id)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border ${
                          markedForReview[activeQuestion.id]
                            ? 'bg-purple-500/15 text-purple-400 border-purple-500/40'
                            : 'bg-bg text-text-muted border-border hover:text-text'
                        }`}
                      >
                        <Flag className="w-3 h-3" />
                        <span>{markedForReview[activeQuestion.id] ? 'Marked' : 'Mark'}</span>
                      </button>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={handlePrevQuestion}
                          className="px-3 py-1 rounded bg-bg border border-border text-xs text-text hover:bg-surface-hover"
                        >
                          Previous
                        </button>
                        <button
                          type="button"
                          onClick={handleNextQuestion}
                          className="px-4 py-1 rounded bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover"
                        >
                          Next
                        </button>
                      </div>
                    </div>

                  </div>
                </div>
              )
            ) : (
              <div className="flex-1 flex items-center justify-center text-text-muted text-xs">
                Select a question from the palette
              </div>
            )}

          </div>

          {/* Right Question Palette Sidebar */}
          <div className="w-64 bg-surface border-l border-border flex flex-col shrink-0 hidden md:flex">
            <div className="p-4 border-b border-border">
              <h4 className="text-xs font-bold text-text uppercase font-mono tracking-wider">Question Palette</h4>
              <div className="grid grid-cols-2 gap-2 mt-2 text-[10px] text-text-muted font-mono">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>Answered</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                  <span>Marked</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span>Visited</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-surface-hover border border-border" />
                  <span>Unvisited</span>
                </div>
              </div>
            </div>

            {/* Questions by Section */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {session.sections.map(sec => {
                const secQs = session.questions.filter(q => q.section_id === sec.id);
                return (
                  <div key={sec.id} className="space-y-2">
                    <span className="text-[11px] font-semibold text-text font-mono truncate block">
                      {sec.name}
                    </span>
                    <div className="grid grid-cols-4 gap-2">
                      {secQs.map((q, qIdx) => {
                        const status = getQuestionStatus(q);
                        const isActive = activeSectionId === sec.id && activeQuestionIndex === qIdx;
                        
                        let badgeColor = 'bg-bg text-text-muted border-border hover:border-text-muted';
                        if (status === 'answered') badgeColor = 'bg-emerald-500 text-white border-emerald-600 font-bold';
                        else if (status === 'marked' || status === 'marked-answered') badgeColor = 'bg-purple-600 text-white border-purple-700 font-bold';

                        return (
                          <button
                            key={q.id}
                            type="button"
                            onClick={() => handleSelectQuestion(sec.id, qIdx)}
                            className={`h-8 rounded-lg text-xs font-mono font-medium border transition-all flex items-center justify-center ${badgeColor} ${
                              isActive ? 'ring-2 ring-accent ring-offset-1 ring-offset-bg' : ''
                            }`}
                          >
                            {qIdx + 1}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* Submit Confirmation Modal */}
        {confirmSubmitModal && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="max-w-md w-full p-6 rounded-2xl bg-surface border border-border space-y-5 shadow-2xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-text">Submit Assessment?</h3>
                  <p className="text-xs text-text-muted">Review your attempt status before confirming</p>
                </div>
              </div>

              {/* Status summary */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs p-3 bg-bg rounded-xl border border-border font-mono">
                <div>
                  <span className="text-text-muted block text-[10px]">TOTAL</span>
                  <strong className="text-text text-sm">{session.total_questions}</strong>
                </div>
                <div>
                  <span className="text-emerald-500 block text-[10px]">ATTEMPTED</span>
                  <strong className="text-emerald-500 text-sm">
                    {Object.keys(mcqAnswers).length + Object.keys(codingResults).length}
                  </strong>
                </div>
                <div>
                  <span className="text-purple-400 block text-[10px]">MARKED</span>
                  <strong className="text-purple-400 text-sm">
                    {Object.values(markedForReview).filter(Boolean).length}
                  </strong>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setConfirmSubmitModal(false)}
                  className="px-4 py-2 rounded-xl border border-border text-text-muted text-xs font-medium hover:text-text hover:bg-surface-hover"
                >
                  Continue Test
                </button>
                <button
                  type="button"
                  onClick={() => handleFinalSubmit(false)}
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 transition-colors cursor-pointer flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  <span>Confirm & Submit</span>
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    );
  }

  // =========================================================================
  // RENDER: SUMMARY & EXPLANATIONS REVIEW STAGE
  // =========================================================================
  if (stage === 'summary' && sessionResult) {
    const filteredQuestions = sessionResult.questions.filter(q => {
      if (reviewFilter === 'all') return true;
      if (reviewFilter === 'correct') return q.is_correct;
      if (reviewFilter === 'incorrect') return q.is_attempted && !q.is_correct;
      if (reviewFilter === 'unattempted') return !q.is_attempted;
      return true;
    });

    return (
      <div className="min-h-screen bg-bg text-text flex flex-col">
        {/* Top Header */}
        <header className="h-16 bg-surface border-b border-border px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/practice')}
              className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text hover:bg-surface-hover"
              title="Return to Practice Hub"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <span className="font-serif text-lg font-bold text-text">intervyn</span>
              <span className="text-border">/</span>
              <span className="text-xs font-mono font-medium text-emerald-500">Assessment Score Report</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleCopyLink}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-bg text-text-muted hover:text-text text-xs font-medium"
          >
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5" />}
            <span>Share Quiz Report</span>
          </button>
        </header>

        {/* Summary Content */}
        <div className="flex-1 max-w-4xl w-full mx-auto p-4 sm:p-8 space-y-6">
          
          {/* Main Score Banner */}
          <div className="p-6 rounded-2xl bg-surface border border-border shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-mono font-semibold text-accent uppercase tracking-wider">Assessment Completed</span>
                <h1 className="text-2xl font-bold font-serif text-text mt-0.5">{sessionResult.title}</h1>
                <p className="text-xs text-text-muted">Time Spent: {Math.floor(sessionResult.time_spent_seconds / 60)}m {sessionResult.time_spent_seconds % 60}s</p>
              </div>

              <div className="flex items-center gap-4 p-4 rounded-xl bg-bg border border-border">
                <div className="text-center">
                  <span className="text-[10px] font-mono text-text-muted block uppercase">Total Score</span>
                  <div className="text-2xl font-bold font-mono text-emerald-500">
                    {sessionResult.total_score} <span className="text-xs text-text-muted">/ {sessionResult.max_possible_score}</span>
                  </div>
                </div>
                <div className="w-[1px] h-8 bg-border" />
                <div className="text-center">
                  <span className="text-[10px] font-mono text-text-muted block uppercase">Accuracy</span>
                  <div className="text-2xl font-bold font-mono text-text">
                    {sessionResult.percentage}%
                  </div>
                </div>
              </div>
            </div>

            {/* Negative Marking Summary */}
            {sessionResult.mcq_summary.incorrect > 0 && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-between text-xs font-mono">
                <span className="text-rose-400">
                  Negative Penalty Incurred: <strong>-{sessionResult.mcq_summary.negative_marking_penalty.toFixed(2)} pts</strong> ({sessionResult.mcq_summary.incorrect} wrong answers × -0.25)
                </span>
                <span className="text-text-muted">Correct: +{sessionResult.mcq_summary.correct}</span>
              </div>
            )}
          </div>

          {/* Section Wise Breakdown */}
          <div className="p-5 rounded-2xl bg-surface border border-border space-y-3">
            <h3 className="text-sm font-bold text-text">Section Breakdown</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {sessionResult.section_stats.map(s => (
                <div key={s.name} className="p-3.5 rounded-xl bg-bg border border-border space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-text">{s.name}</span>
                    <span className="font-mono text-accent font-bold">{s.score} / {s.max_score} pts</span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-surface overflow-hidden">
                    <div 
                      className="h-full bg-accent rounded-full transition-all"
                      style={{ width: `${Math.max(0, Math.min(100, s.percentage))}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-text-muted font-mono">
                    <span>Correct: {s.correct}</span>
                    <span>Incorrect: {s.incorrect}</span>
                    <span>Accuracy: {s.percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Detailed Question Review */}
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-text">Comprehensive Question Review</h3>
                <p className="text-xs text-text-muted">Inspect correct solutions, candidate choices, and official explanations</p>
              </div>

              {/* Review Filter Tabs */}
              <div className="flex items-center gap-1 p-1 bg-surface rounded-xl border border-border text-xs">
                {(['all', 'incorrect', 'correct', 'unattempted'] as const).map(tab => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setReviewFilter(tab)}
                    className={`px-3 py-1 rounded-lg capitalize font-medium transition-colors ${
                      reviewFilter === tab
                        ? 'bg-accent text-accent-contrast shadow-xs'
                        : 'text-text-muted hover:text-text'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            {/* Questions List */}
            <div className="space-y-4">
              {filteredQuestions.map((q, idx) => (
                <div key={q.id} className="p-5 rounded-2xl bg-surface border border-border space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-accent">Question {idx + 1}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider bg-bg border border-border text-text-muted">
                        {q.type.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                        q.is_correct
                          ? 'bg-emerald-500/10 text-emerald-500'
                          : q.is_attempted
                          ? 'bg-rose-500/10 text-rose-500'
                          : 'bg-bg text-text-muted'
                      }`}>
                        {q.is_correct ? `+${q.points_awarded.toFixed(2)} Pts` : q.is_attempted ? `${q.points_awarded.toFixed(2)} Pts` : '0.00 Pts (Skipped)'}
                      </span>
                    </div>
                  </div>

                  <div className="text-sm font-medium text-text leading-relaxed">
                    {q.title || q.question}
                  </div>

                  {q.code_snippet && (
                    <MCQCodeBlock code={q.code_snippet} />
                  )}

                  {/* MCQ Options Display */}
                  {q.type === 'mcq' && q.options && (
                    <div className="space-y-2 pt-1">
                      {Object.entries(q.options).map(([optKey, optText]) => {
                        const isCorrectOpt = optKey === q.correct_answer || optKey === (q as any).correct_option;
                        const isUserChoice = optKey === q.user_answer;

                        let style = 'bg-bg border-border text-text-muted';
                        if (isCorrectOpt) style = 'bg-emerald-500/15 border-emerald-500 text-text font-medium';
                        else if (isUserChoice && !isCorrectOpt) style = 'bg-rose-500/15 border-rose-500 text-text';

                        return (
                          <div key={optKey} className={`p-3 rounded-xl border text-xs flex items-center justify-between ${style}`}>
                            <div className="flex items-center gap-2.5">
                              <span className="w-5 h-5 rounded-full bg-surface border border-border font-mono font-bold text-[11px] flex items-center justify-center">
                                {optKey}
                              </span>
                              <span>{optText}</span>
                            </div>
                            <div className="text-[10px] font-mono font-bold">
                              {isCorrectOpt && <span className="text-emerald-400">CORRECT ANSWER</span>}
                              {isUserChoice && !isCorrectOpt && <span className="text-rose-400">YOUR CHOICE</span>}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Official Explanation Box */}
                  {q.explanation && (
                    <div className="p-3.5 rounded-xl bg-bg border border-border space-y-1 text-xs">
                      <span className="font-semibold text-accent font-mono">Official Explanation:</span>
                      <p className="text-text-muted leading-relaxed">{q.explanation}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Bottom Actions */}
          <div className="flex justify-between pt-4 border-t border-border">
            <button
              type="button"
              onClick={() => navigate('/practice')}
              className="px-4 py-2 rounded-xl border border-border text-xs text-text-muted hover:text-text hover:bg-surface"
            >
              Back to Problems
            </button>
            <button
              type="button"
              onClick={() => {
                setStage('briefing');
                setSessionResult(null);
              }}
              className="px-5 py-2 rounded-xl bg-accent text-accent-contrast text-xs font-medium hover:bg-accent-hover transition-colors"
            >
              Retake Practice
            </button>
          </div>

        </div>
      </div>
    );
  }

  // =========================================================================
  // RENDER: CONFIG MODAL TRIGGER IF NO SESSION ID
  // =========================================================================
  return (
    <TimedPracticeConfigModal
      isOpen={configModalOpen}
      onClose={() => {
        setConfigModalOpen(false);
        navigate('/practice');
      }}
    />
  );
};
